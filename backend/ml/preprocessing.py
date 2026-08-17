"""Pipeline praproses data untuk dataset primer dan benchmark."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedData:
    """Output standar dari semua hasil praproses.

    Attributes
    ----------
    transactions : pd.DataFrame
        Kolom yang diharapkan:
        - order_id (str): ID unik transaksi
        - timestamp (pd.Timestamp): waktu pesanan
        - itemset (list[str]): kategori dalam pesanan
        - n_items (int): jumlah kategori unik
    binary_matrix : pd.DataFrame
        One-hot matrix (baris = order_id, kolom = kategori unik, nilai = 0/1).
    metadata : dict
        Statistik dataset: nama, jumlah transaksi, proporsi single-item, dll.
    """

    transactions: pd.DataFrame
    binary_matrix: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        n_tx = len(self.transactions)
        n_items = len(self.binary_matrix.columns)
        name = self.metadata.get("dataset_name", "unknown")
        return f"PreprocessedData({name}: {n_tx} transaksi, {n_items} item unik)"


# status pesanan yang dianggap valid (benar-benar diproses/dikirim)
_VALID_STATUSES = {"Selesai", "Sedang Dikirim", "Telah Dikirim"}


def _is_valid_status(status: str) -> bool:
    if status in _VALID_STATUSES:
        return True
    if isinstance(status, str) and status.startswith("Pesanan diterima"):
        return True
    return False


def _filter_status(df: pd.DataFrame) -> pd.DataFrame:
    """Buang pesanan berstatus batal, hanya pertahankan yang benar-benar terpenuhi."""
    mask = df["Status Pesanan"].apply(_is_valid_status)
    df_valid = df[mask].copy()
    n_dropped = len(df) - len(df_valid)
    logger.info("filter status: %d -> %d baris (buang %d batal)", len(df), len(df_valid), n_dropped)
    return df_valid


def _parse_itemset(df: pd.DataFrame) -> pd.DataFrame:
    """Parse kolom product_categories (comma-separated string) menjadi list per order."""
    def _parse(cats: str) -> list[str]:
        if pd.isna(cats) or str(cats).strip() == "":
            return []
        return [c.strip() for c in str(cats).split(",") if c.strip()]

    df = df.copy()
    df["itemset"] = df["product_categories"].apply(_parse)
    df["n_items"] = df["itemset"].apply(len)

    empty_mask = df["n_items"] == 0
    n_empty = empty_mask.sum()
    if n_empty > 0:
        logger.warning("%d baris tanpa itemset setelah parsing, dibuang", n_empty)
        df = df[~empty_mask]

    logger.info("parse itemset: %d transaksi, %d kategori unik", len(df), df["itemset"].explode().nunique())
    return df


def _impute_timestamps(
    df: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    """Imputasi timestamp kosong berdasarkan pola distribusi bulan referensi terdekat.

    Bulan target diidentifikasi dari nama file (format: "DecemberSales2024.xlsx").
    Imputasi dipilih daripada drop karena bobot temporal exp-decay smooth pada resolusi bulanan,
    imprecision hari dalam satu bulan tidak signifikan terhadap bobot akhir.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["Waktu Pesanan Dibuat"], errors="coerce")
    df["is_imputed"] = False

    na_mask = df["timestamp"].isna()
    n_na = na_mask.sum()
    if n_na == 0:
        logger.info("tidak ada timestamp NaN, skip imputasi")
        return df

    _MONTH_MAP = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
    }

    na_sources = df.loc[na_mask, "source_file"].unique()
    logger.info("imputasi timestamp: %d baris NaN dari %s", n_na, list(na_sources))

    valid_df = df[~na_mask]

    for src in na_sources:
        src_mask = na_mask & (df["source_file"] == src)
        n_src = src_mask.sum()

        # parse bulan dan tahun dari nama file, misal "DecemberSales2024.xlsx"
        month_name = None
        year = None
        for m_name in _MONTH_MAP:
            if src.startswith(m_name):
                month_name = m_name
                year_str = src.replace(m_name + "Sales", "").replace(".xlsx", "")
                year = int(year_str)
                break

        if month_name is None or year is None:
            logger.warning("tidak bisa parse bulan/tahun dari '%s', baris dibuang", src)
            df.loc[src_mask, "timestamp"] = pd.NaT
            continue

        target_month = _MONTH_MAP[month_name]
        target_start = pd.Timestamp(year=year, month=target_month, day=1)
        if target_month == 12:
            target_end = pd.Timestamp(year=year + 1, month=1, day=1)
        else:
            target_end = pd.Timestamp(year=year, month=target_month + 1, day=1)
        n_days = (target_end - target_start).days

        ref_before = target_start - relativedelta(months=1)
        ref_after = target_end
        ref_after_end = ref_after + relativedelta(months=1)

        ref_data = valid_df[
            ((valid_df["timestamp"] >= ref_before)
             & (valid_df["timestamp"] < target_start))
            | ((valid_df["timestamp"] >= ref_after)
               & (valid_df["timestamp"] < ref_after_end))
        ]

        if len(ref_data) > 0:
            ref_days = ref_data["timestamp"].dt.day
            day_counts = ref_days.value_counts().sort_index()
            valid_days = [d for d in day_counts.index if d <= n_days]
            if not valid_days:
                valid_days = list(range(1, n_days + 1))
                day_probs = np.ones(len(valid_days)) / len(valid_days)
            else:
                day_probs = np.array([day_counts.get(d, 0) for d in valid_days], dtype=float)
                day_probs /= day_probs.sum()
        else:
            valid_days = list(range(1, n_days + 1))
            day_probs = np.ones(len(valid_days)) / len(valid_days)

        sampled_days = rng.choice(valid_days, size=n_src, p=day_probs)

        if len(ref_data) > 0:
            ref_hours = ref_data["timestamp"].dt.hour.values
            sampled_hours = rng.choice(ref_hours, size=n_src)
        else:
            sampled_hours = rng.integers(7, 23, size=n_src)  # jam kerja

        sampled_minutes = rng.integers(0, 60, size=n_src)

        imputed_ts = [
            pd.Timestamp(year=year, month=target_month, day=int(d),
                         hour=int(h), minute=int(m))
            for d, h, m in zip(sampled_days, sampled_hours, sampled_minutes)
        ]

        df.loc[src_mask, "timestamp"] = imputed_ts
        df.loc[src_mask, "is_imputed"] = True

        logger.info(
            "  %s -> %d baris diimputasi ke %s %d (hari 1-%d, ref %d baris)",
            src, n_src, month_name, year, n_days, len(ref_data),
        )

    still_na = df["timestamp"].isna().sum()
    if still_na > 0:
        logger.warning("%d baris masih NaN setelah imputasi, dibuang", still_na)
        df = df[df["timestamp"].notna()]

    return df


def _standardize_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """Konversi dan imputasi timestamp."""
    df = _impute_timestamps(df)

    n_imputed = df["is_imputed"].sum()
    logger.info(
        "timestamp: %d transaksi (%d diimputasi), rentang %s s/d %s",
        len(df), n_imputed,
        df["timestamp"].min().strftime("%Y-%m-%d"),
        df["timestamp"].max().strftime("%Y-%m-%d"),
    )
    return df


def _normalize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Strip dan collapse whitespace pada nama kategori.

    Nama dengan '/' seperti 'Mangkok Sambal / Saus' sengaja dibiarkan."""
    def _normalize(cats: list[str]) -> list[str]:
        normalized = []
        for c in cats:
            c = c.strip()
            c = re.sub(r"\s+", " ", c)
            normalized.append(c)
        return normalized

    df = df.copy()
    df["itemset"] = df["itemset"].apply(_normalize)
    df["n_items"] = df["itemset"].apply(len)

    logger.info("normalisasi kategori: %d kategori unik", df["itemset"].explode().nunique())
    return df


def _handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Isi NaN kolom biaya dengan 0, tidak menyentuh kolom kategori."""
    cost_cols = [
        "Total Diskon",
        "Ongkos Kirim Dibayar oleh Pembeli",
        "Estimasi Potongan Biaya Pengiriman",
        "Total Pembayaran",
        "Perkiraan Ongkos Kirim",
    ]
    df = df.copy()
    for col in cost_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def preprocess_primary(df: pd.DataFrame) -> PreprocessedData:
    """Praproses dataset primer Indonesia E-Commerce (all_months_clean.csv).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame mentah dari load_primary_dataset(), separator ';'.

    Returns
    -------
    PreprocessedData
    """
    n_original = len(df)
    logger.info("praproses primer: %d baris", n_original)

    df = _filter_status(df)
    df = _parse_itemset(df)
    df = _standardize_temporal(df)
    df = _normalize_categories(df)
    df = _handle_missing(df)

    tx_cols = ["order_id", "timestamp", "itemset", "n_items", "is_imputed"]
    transactions = df[tx_cols].copy()
    transactions = transactions.sort_values("timestamp").reset_index(drop=True)

    binary_matrix = build_binary_matrix(transactions)

    n_single = (transactions["n_items"] == 1).sum()
    n_multi = (transactions["n_items"] > 1).sum()
    all_items = transactions["itemset"].explode().unique()
    n_imputed = transactions["is_imputed"].sum()

    metadata = {
        "dataset_name": "Indonesia E-Commerce (Primer)",
        "n_original_rows": n_original,
        "n_transactions": len(transactions),
        "n_items_unique": len(all_items),
        "n_single_item_orders": n_single,
        "n_multi_item_orders": n_multi,
        "pct_single_item_orders": n_single / len(transactions) * 100,
        "pct_multi_item_orders": n_multi / len(transactions) * 100,
        "n_imputed_rows": int(n_imputed),
        "timestamp_min": str(transactions["timestamp"].min()),
        "timestamp_max": str(transactions["timestamp"].max()),
        "rows_dropped_total": n_original - len(transactions),
        "pct_rows_dropped": (n_original - len(transactions)) / n_original * 100,
    }

    logger.info(
        "primer selesai: %d -> %d transaksi (%.1f%% dipertahankan)",
        n_original, len(transactions), len(transactions) / n_original * 100,
    )
    logger.info(
        "  single-item: %d (%.1f%%), multi-item: %d (%.1f%%)",
        n_single, metadata["pct_single_item_orders"],
        n_multi, metadata["pct_multi_item_orders"],
    )

    return PreprocessedData(
        transactions=transactions,
        binary_matrix=binary_matrix,
        metadata=metadata,
    )


def preprocess_benchmark(df: pd.DataFrame) -> PreprocessedData:
    """Praproses dataset benchmark UCI Online Retail II.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame gabungan dari load_benchmark_dataset(), semua sheet online_retail_II.xlsx.

    Returns
    -------
    PreprocessedData
    """
    n_original = len(df)
    logger.info("praproses benchmark: %d baris", n_original)

    df = df.copy()
    df["Invoice_str"] = df["Invoice"].astype(str)
    cancel_mask = df["Invoice_str"].str.startswith("C")
    n_cancel = cancel_mask.sum()
    df = df[~cancel_mask]
    logger.info("buang %d invoice pembatalan (awalan 'C'), tersisa %d", n_cancel, len(df))

    df["timestamp"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    invalid_ts = df["timestamp"].isna().sum()
    if invalid_ts > 0:
        logger.info("buang %d baris tanpa timestamp valid", invalid_ts)
        df = df[df["timestamp"].notna()]

    qty_invalid = (df["Quantity"] <= 0).sum()
    if qty_invalid > 0:
        logger.info("buang %d baris dengan Quantity <= 0", qty_invalid)
        df = df[df["Quantity"] > 0]

    grouped = (
        df.groupby("Invoice_str")
        .agg(
            timestamp=("timestamp", "first"),
            itemset=("StockCode", lambda x: list(x.astype(str).unique())),
        )
        .reset_index()
    )
    grouped = grouped.rename(columns={"Invoice_str": "order_id"})
    grouped["n_items"] = grouped["itemset"].apply(len)

    logger.info("agregasi: %d invoice, %d StockCode unik", len(grouped), grouped["itemset"].explode().nunique())

    # normalisasi tidak diperlukan (sudah di level SKU)

    transactions = grouped[["order_id", "timestamp", "itemset", "n_items"]].copy()
    transactions = transactions.sort_values("timestamp").reset_index(drop=True)

    binary_matrix = build_binary_matrix(transactions)

    n_single = (transactions["n_items"] == 1).sum()
    n_multi = (transactions["n_items"] > 1).sum()
    all_items = transactions["itemset"].explode().unique()

    metadata = {
        "dataset_name": "UCI Online Retail II (Benchmark)",
        "n_original_rows": n_original,
        "n_transactions": len(transactions),
        "n_items_unique": len(all_items),
        "n_single_item_orders": n_single,
        "n_multi_item_orders": n_multi,
        "pct_single_item_orders": n_single / len(transactions) * 100 if len(transactions) > 0 else 0,
        "pct_multi_item_orders": n_multi / len(transactions) * 100 if len(transactions) > 0 else 0,
        "timestamp_min": str(transactions["timestamp"].min()),
        "timestamp_max": str(transactions["timestamp"].max()),
        "rows_dropped_cancel": n_cancel,
        "rows_dropped_invalid_ts": invalid_ts,
        "rows_dropped_invalid_qty": qty_invalid,
    }

    logger.info("benchmark selesai: %d baris -> %d transaksi", n_original, len(transactions))

    return PreprocessedData(
        transactions=transactions,
        binary_matrix=binary_matrix,
        metadata=metadata,
    )


def build_binary_matrix(transactions: pd.DataFrame) -> pd.DataFrame:
    """Buat one-hot matrix dari transactions.

    Parameters
    ----------
    transactions : pd.DataFrame
        Harus punya kolom order_id (str) dan itemset (list[str]).

    Returns
    -------
    pd.DataFrame
        Baris = order_id, kolom = kategori unik, nilai = 0/1.
    """
    exploded = transactions[["order_id", "itemset"]].explode("itemset")
    exploded = exploded.dropna(subset=["itemset"])
    exploded["value"] = 1

    matrix = exploded.pivot_table(
        index="order_id",
        columns="itemset",
        values="value",
        aggfunc="max",
        fill_value=0,
    )

    matrix = matrix.astype(np.int8)
    matrix = matrix[sorted(matrix.columns)]

    logger.info("binary matrix: %d transaksi x %d item", matrix.shape[0], matrix.shape[1])
    return matrix


def load_primary_dataset(path: str) -> pd.DataFrame:
    """Muat dataset primer dari CSV (separator ';', encoding UTF-8 BOM)."""
    return pd.read_csv(path, sep=";", encoding="utf-8-sig")


def load_benchmark_dataset(path: str) -> pd.DataFrame:
    """Muat dataset benchmark dari XLSX (gabungkan semua sheet)."""
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    return pd.concat(sheets.values(), ignore_index=True)
