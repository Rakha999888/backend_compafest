from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

@dataclass
class RuleResult:
    rule_name: str
    passed: bool
    total_rows: int
    failing_rows: int
    message: str

    @property
    def failing_pct(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return self.failing_rows / self.total_rows * 100

@dataclass
class ValidationReport:
    dataset_name: str
    total_rows: int
    results: list[RuleResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def critical_failures(self) -> list[RuleResult]:
        return [r for r in self.results if not r.passed]

    def summary(self) -> str:
        status = "OK" if self.all_passed else "GAGAL"
        lines = [
            f"Validasi: {self.dataset_name}",
            f"  Total baris : {self.total_rows}",
            f"  Aturan      : {len(self.results)}",
            f"  Status      : {status}",
            "",
        ]
        for r in self.results:
            tag = "OK" if r.passed else "GAGAL"
            lines.append(f"  [{tag}] {r.rule_name}")
            lines.append(f"        Baris gagal: {r.failing_rows} ({r.failing_pct:.2f}%)")
            lines.append(f"        {r.message}")
            lines.append("")
        return "\n".join(lines)


# Toleransi default validasi.
TOLERANCE_CONFIG = {
    # Baris dengan product_categories kosong pada status "Selesai" dibuang.
    "drop_empty_categories_on_selesai": True,

    # timestamp tidak valid diimputasi dulu di preprocessing, lalu dibuang hanya jika imputasi gagal
    "drop_invalid_timestamps": True,

    # outlier total_qty dan total_weight_gr: ditandai saja, bisa jadi pesanan grosir valid
    "outlier_action": "flag",  # pilihan: "flag", "drop", "winsorize"

    "outlier_percentile": 99,
}


def validate_primary_dataset(
    df: pd.DataFrame,
    tolerance: Optional[dict] = None,
) -> ValidationReport:
    """Validasi dataset primer Indonesia E-Commerce Sales & Shipping 2023-2025."""
    cfg = {**TOLERANCE_CONFIG, **(tolerance or {})}
    report = ValidationReport(
        dataset_name="Indonesia E-Commerce Sales & Shipping 2023-2025",
        total_rows=len(df),
    )

    # order_id unik
    dup_count = df["order_id"].duplicated().sum()
    report.results.append(
        RuleResult(
            rule_name="order_id unik",
            passed=dup_count == 0,
            total_rows=len(df),
            failing_rows=dup_count,
            message=(
                "Tidak ada duplikasi."
                if dup_count == 0
                else f"Ditemukan {dup_count} baris duplikat order_id."
            ),
        )
    )

    # product_categories tidak kosong pada status "Selesai"
    selesai_mask = df["Status Pesanan"] == "Selesai"
    selesai_df = df[selesai_mask]
    cats_na = selesai_df["product_categories"].isna()
    cats_blank = selesai_df["product_categories"].astype(str).str.strip() == ""
    cats_empty = (cats_na | cats_blank).sum()
    report.results.append(
        RuleResult(
            rule_name="product_categories tidak kosong pada 'Selesai'",
            passed=cats_empty == 0,
            total_rows=len(selesai_df),
            failing_rows=cats_empty,
            message=(
                "Semua baris 'Selesai' memiliki product_categories."
                if cats_empty == 0
                else f"{cats_empty} baris 'Selesai' dengan kategori kosong. "
                f"Tindakan: {'buang' if cfg['drop_empty_categories_on_selesai'] else 'pertahankan'}."
            ),
        )
    )

    # waktu pesanan dibuat valid
    ts_parsed = pd.to_datetime(df["Waktu Pesanan Dibuat"], errors="coerce")
    ts_invalid = ts_parsed.isna().sum()
    original_na = df["Waktu Pesanan Dibuat"].isna().sum()
    report.results.append(
        RuleResult(
            rule_name="Waktu Pesanan Dibuat dapat diparse menjadi timestamp",
            passed=ts_invalid == 0,
            total_rows=len(df),
            failing_rows=ts_invalid,
            message=(
                "Semua timestamp valid."
                if ts_invalid == 0
                else f"{ts_invalid} baris ({ts_invalid/len(df)*100:.2f}%) timestamp tidak valid "
                f"(termasuk {original_na} NaN asli). "
                "Preprocessing akan mencoba imputasi."
            ),
        )
    )

    # tidak ada negatif pada total_qty dan total_weight_gr
    for col in ["total_qty", "total_weight_gr"]:
        series = pd.to_numeric(df[col], errors="coerce")
        neg_count = (series < 0).sum()
        report.results.append(
            RuleResult(
                rule_name=f"{col} tidak negatif",
                passed=neg_count == 0,
                total_rows=len(df),
                failing_rows=neg_count,
                message=(
                    f"Tidak ada nilai negatif pada {col}."
                    if neg_count == 0
                    else f"{neg_count} baris dengan {col} negatif."
                ),
            )
        )

    # status pesanan hanya berisi nilai yang diharapkan
    known_statuses = {"Selesai", "Batal", "Sedang Dikirim", "Telah Dikirim"}
    actual_statuses = set(df["Status Pesanan"].dropna().unique())
    unknown = set()
    for s in actual_statuses:
        if s not in known_statuses and not s.startswith("Pesanan diterima"):
            unknown.add(s)

    report.results.append(
        RuleResult(
            rule_name="Status Pesanan berisi nilai yang diharapkan",
            passed=len(unknown) == 0,
            total_rows=len(df),
            failing_rows=df["Status Pesanan"].isin(unknown).sum() if unknown else 0,
            message=(
                f"Semua status dikenali. Nilai unik: {sorted(actual_statuses)[:5]}..."
                if len(unknown) == 0
                else f"Status tidak dikenali: {unknown}"
            ),
        )
    )

    # deteksi outlier
    for col in ["total_qty", "total_weight_gr"]:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        p = cfg["outlier_percentile"]
        threshold = series.quantile(p / 100)
        outlier_count = (series > threshold).sum()
        report.results.append(
            RuleResult(
                rule_name=f"Outlier {col} (>persentil ke-{p})",
                passed=True,
                total_rows=len(series),
                failing_rows=outlier_count,
                message=(
                    f"Ambang P{p}: {threshold:.0f}. "
                    f"{outlier_count} baris di atas ambang. "
                    f"Tindakan: {cfg['outlier_action']}."
                ),
            )
        )

    return report


def validate_benchmark_dataset(df: pd.DataFrame) -> ValidationReport:
    """Validasi dataset benchmark UCI Online Retail II."""
    report = ValidationReport(
        dataset_name="UCI Online Retail II",
        total_rows=len(df),
    )

    # Invoice dan StockCode tidak kosong
    inv_na = df["Invoice"].isna().sum()
    sc_na = df["StockCode"].isna().sum()
    combined_na = (df["Invoice"].isna() | df["StockCode"].isna()).sum()
    report.results.append(
        RuleResult(
            rule_name="Invoice dan StockCode tidak kosong",
            passed=combined_na == 0,
            total_rows=len(df),
            failing_rows=combined_na,
            message=(
                "Semua Invoice dan StockCode terisi."
                if combined_na == 0
                else f"Invoice kosong: {inv_na}, StockCode kosong: {sc_na}."
            ),
        )
    )

    # InvoiceDate valid
    ts_parsed = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    ts_invalid = ts_parsed.isna().sum()
    report.results.append(
        RuleResult(
            rule_name="InvoiceDate dapat diparse menjadi timestamp",
            passed=ts_invalid == 0,
            total_rows=len(df),
            failing_rows=ts_invalid,
            message=(
                "Semua timestamp valid."
                if ts_invalid == 0
                else f"{ts_invalid} baris timestamp tidak valid."
            ),
        )
    )

    # Quantity tidak nol pada non-pembatalan
    non_cancel = df[~df["Invoice"].astype(str).str.startswith("C")]
    qty_zero = (non_cancel["Quantity"] == 0).sum()
    report.results.append(
        RuleResult(
            rule_name="Quantity tidak nol pada non-pembatalan",
            passed=qty_zero == 0,
            total_rows=len(non_cancel),
            failing_rows=qty_zero,
            message=(
                "Tidak ada Quantity bernilai nol pada non-pembatalan."
                if qty_zero == 0
                else f"{qty_zero} baris non-pembatalan dengan Quantity = 0."
            ),
        )
    )

    # Customer ID kosong
    cid_na = df["Customer ID"].isna().sum()
    report.results.append(
        RuleResult(
            rule_name="Customer ID terisi",
            passed=True,
            total_rows=len(df),
            failing_rows=cid_na,
            message=(
                f"{cid_na} baris ({cid_na/len(df)*100:.2f}%) tanpa Customer ID. "
                "Tidak diperlukan untuk pipeline ARM."
            ),
        )
    )

    return report