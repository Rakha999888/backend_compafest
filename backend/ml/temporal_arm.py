"""Association Rule Mining berbobot temporal untuk menghasilkan matriks afinitas antar kategori."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ml.config import (
    HALF_LIFE_DAYS,
    MIN_CONFIDENCE,
    MIN_SUPPORT,
    W1,
    W2,
)

logger = logging.getLogger(__name__)

@dataclass
class AffinityMatrix:
    """Matriks afinitas NxN antar-pasangan kategori."""

    matrix: np.ndarray            # matriks simetris NxN, skor afinitas
    categories: list[str]         # urutan sesuai indeks matriks
    rules: pd.DataFrame           # aturan asosiasi yang mendasari
    metadata: dict[str, Any] = field(default_factory=dict)

    # Pre-built lookup table untuk O(1) category -> index mapping.
    _cat_to_idx: dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self._cat_to_idx:
            self._cat_to_idx = {
                cat: idx for idx, cat in enumerate(self.categories)
            }

    def get_affinity(self, cat_a: str, cat_b: str) -> float:
        """Ambil skor afinitas antara dua kategori (O(1) lookup)."""
        i = self._cat_to_idx.get(cat_a)
        j = self._cat_to_idx.get(cat_b)
        if i is None or j is None:
            return 0.0
        return float(self.matrix[i, j])

    def get_category_indices(self, cats: list[str]) -> np.ndarray:
        """Mengambil array indeks, kategori tidak dikenali dilewati."""
        return np.array(
            [self._cat_to_idx[c] for c in cats if c in self._cat_to_idx],
            dtype=np.intp,
        )

    def get_upper_triangle_sum(self, cats: list[str]) -> float:
        """Jumlah afinitas upper-triangle subset kategori, dipakai oleh compute_fitness()."""
        indices = self.get_category_indices(cats)
        if len(indices) < 2:
            return 0.0
        sub = self.matrix[np.ix_(indices, indices)]
        return float(np.triu(sub, k=1).sum())

    def top_pairs(self, n: int = 10) -> list[tuple[str, str, float]]:
        """Ambil N pasangan dengan afinitas tertinggi."""
        pairs = []
        n_cats = len(self.categories)
        for i in range(n_cats):
            for j in range(i + 1, n_cats):
                if self.matrix[i, j] > 0:
                    pairs.append(
                        (self.categories[i], self.categories[j],
                         float(self.matrix[i, j]))
                    )
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs[:n]

def compute_temporal_weights(
    timestamps: pd.Series,
    half_life_days: float = HALF_LIFE_DAYS,
) -> np.ndarray:
    """Bobot exponential decay per transaksi: exp(-ln(2)/H * usia_hari)."""
    t_ref = timestamps.max()
    age_days = (t_ref - timestamps).dt.total_seconds() / 86400.0
    lam = np.log(2) / half_life_days
    weights = np.exp(-lam * age_days.values)
    return weights

class _WeightedFPNode:
    """Node pada weighted FP-Tree."""

    __slots__ = ("item", "weight", "parent", "children", "link")

    def __init__(self, item: str | None, weight: float, parent: "_WeightedFPNode | None"):
        self.item = item
        self.weight = weight
        self.parent = parent
        self.children: dict[str, _WeightedFPNode] = {}
        self.link: _WeightedFPNode | None = None

class WeightedFPTree:
    """FP-Tree yang mengakumulasi bobot transaksi, bukan hitungan biner."""

    def __init__(self):
        self.root = _WeightedFPNode(None, 0.0, None)
        self.header_table: dict[str, _WeightedFPNode] = {}
        self.item_weights: dict[str, float] = defaultdict(float)
        self.total_weight: float = 0.0

    def insert(self, items: list[str], weight: float) -> None:
        """Masukkan transaksi berbobot ke dalam tree."""
        self.total_weight += weight
        node = self.root
        for item in items:
            self.item_weights[item] += weight
            if item in node.children:
                node.children[item].weight += weight
                node = node.children[item]
            else:
                new_node = _WeightedFPNode(item, weight, node)
                node.children[item] = new_node
                if item in self.header_table:
                    current = self.header_table[item]
                    while current.link is not None:
                        current = current.link
                    current.link = new_node
                else:
                    self.header_table[item] = new_node
                node = new_node

    def _get_prefix_paths(self, item: str) -> list[tuple[list[str], float]]:
        """Dapatkan prefix paths untuk item tertentu."""
        paths = []
        node = self.header_table.get(item)
        while node is not None:
            prefix = []
            parent = node.parent
            while parent is not None and parent.item is not None:
                prefix.append(parent.item)
                parent = parent.parent
            if prefix:
                prefix.reverse()
                paths.append((prefix, node.weight))
            node = node.link
        return paths

def weighted_fpgrowth(
    binary_matrix: pd.DataFrame,
    weights: np.ndarray,
    min_support: float = MIN_SUPPORT,
) -> pd.DataFrame:
    """Mining weighted frequent itemsets menggunakan FP-Tree kustom."""
    items = list(binary_matrix.columns)
    total_weight = weights.sum()
    min_weight = min_support * total_weight

    item_weights = {}
    for item in items:
        col = binary_matrix[item].values
        w = (col * weights).sum()
        if w >= min_weight:
            item_weights[item] = w

    sorted_items = sorted(item_weights, key=item_weights.get, reverse=True)

    tree = WeightedFPTree()
    for idx in range(len(binary_matrix)):
        row = binary_matrix.iloc[idx]
        tx_items = [item for item in sorted_items if row[item] > 0]
        if tx_items:
            tree.insert(tx_items, weights[idx])

    freq_itemsets = []

    def _mine(tree: WeightedFPTree, prefix: frozenset, min_w: float):
        for item in sorted(tree.header_table, key=lambda x: tree.item_weights.get(x, 0)):
            new_prefix = prefix | frozenset([item])
            support = tree.item_weights.get(item, 0) / total_weight
            if tree.item_weights.get(item, 0) >= min_w:
                freq_itemsets.append({
                    "support": support,
                    "itemsets": new_prefix,
                })

                paths = tree._get_prefix_paths(item)
                if paths:
                    cond_tree = WeightedFPTree()
                    cond_tree.total_weight = total_weight
                    for path_items, path_weight in paths:
                        cond_tree.insert(path_items, path_weight)

                    valid_items = {
                        i for i, w in cond_tree.item_weights.items()
                        if w >= min_w
                    }
                    if valid_items:
                        _mine(cond_tree, new_prefix, min_w)

    _mine(tree, frozenset(), min_weight)

    if not freq_itemsets:
        return pd.DataFrame(columns=["support", "itemsets"])

    return pd.DataFrame(freq_itemsets)

def weighted_association_rules(
    freq_itemsets: pd.DataFrame,
    binary_matrix: pd.DataFrame,
    weights: np.ndarray,
    min_confidence: float = MIN_CONFIDENCE,
) -> pd.DataFrame:
    """Generate aturan asosiasi dari weighted frequent itemsets."""
    if len(freq_itemsets) == 0:
        return pd.DataFrame()

    total_weight = weights.sum()

    # Pre-compute numpy arrays sekali untuk eliminasi DataFrame overhead
    _bm_values = binary_matrix.values
    _col_map = {c: i for i, c in enumerate(binary_matrix.columns)}

    def _wsupport(itemset: frozenset) -> float:
        """Weighted support via numpy vectorized boolean indexing."""
        indices = [_col_map[item] for item in itemset if item in _col_map]
        if not indices:
            return 0.0
        mask = _bm_values[:, indices].all(axis=1)
        return weights[mask].sum() / total_weight

    support_cache = {}
    for _, row in freq_itemsets.iterrows():
        itemset = row["itemsets"]
        support_cache[itemset] = row["support"]

    rules = []
    for _, row in freq_itemsets.iterrows():
        itemset = row["itemsets"]
        if len(itemset) < 2:
            continue

        for item in itemset:
            antecedent = itemset - frozenset([item])
            consequent = frozenset([item])

            sup_ante = support_cache.get(antecedent) or _wsupport(antecedent)
            sup_cons = support_cache.get(consequent) or _wsupport(consequent)

            if sup_ante <= 0 or sup_cons <= 0:
                continue

            confidence = row["support"] / sup_ante
            if confidence < min_confidence:
                continue

            lift = confidence / sup_cons
            rules.append({
                "antecedents": antecedent,
                "consequents": consequent,
                "support": row["support"],
                "confidence": confidence,
                "lift": lift,
            })

    if not rules:
        return pd.DataFrame()

    return pd.DataFrame(rules)

def run_weighted_arm_custom(
    binary_matrix: pd.DataFrame,
    weights: np.ndarray,
    min_support: float = MIN_SUPPORT,
    min_confidence: float = MIN_CONFIDENCE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Jalankan ARM berbobot temporal via weighted FP-Growth kustom (Pendekatan A)."""
    freq = weighted_fpgrowth(binary_matrix, weights, min_support)
    if len(freq) == 0:
        return freq, pd.DataFrame()

    rules = weighted_association_rules(
        freq, binary_matrix, weights, min_confidence
    )
    return freq, rules


def compute_affinity_matrix(
    rules: pd.DataFrame,
    categories: list[str],
    w1: float = W1,
    w2: float = W2,
) -> AffinityMatrix:
    """Bangun matriks afinitas NxN dari aturan asosiasi (min-max normalized)."""
    n = len(categories)
    cat_to_idx = {c: i for i, c in enumerate(categories)}

    pair_support: dict[tuple[int, int], float] = {}
    pair_lift: dict[tuple[int, int], float] = {}

    if len(rules) > 0:
        for _, rule in rules.iterrows():
            ante = set(rule["antecedents"])
            cons = set(rule["consequents"])
            all_items = ante | cons

            if len(all_items) == 2:
                items = sorted(all_items)
                if items[0] in cat_to_idx and items[1] in cat_to_idx:
                    i, j = cat_to_idx[items[0]], cat_to_idx[items[1]]
                    key = (min(i, j), max(i, j))
                    if key not in pair_support or rule["support"] > pair_support[key]:
                        pair_support[key] = rule["support"]
                    if key not in pair_lift or rule["lift"] > pair_lift[key]:
                        pair_lift[key] = rule["lift"]

    def _minmax_normalize(values: dict) -> dict:
        if not values:
            return {}
        vals = list(values.values())
        v_min, v_max = min(vals), max(vals)
        if v_max - v_min < 1e-12:
            return {k: 0.5 for k in values}
        return {k: (v - v_min) / (v_max - v_min) for k, v in values.items()}

    sup_norm = _minmax_normalize(pair_support)
    lift_norm = _minmax_normalize(pair_lift)

    matrix = np.zeros((n, n), dtype=np.float64)
    for key in set(list(sup_norm.keys()) + list(lift_norm.keys())):
        i, j = key
        s = sup_norm.get(key, 0.0)
        l = lift_norm.get(key, 0.0)
        aff = w1 * s + w2 * l
        matrix[i, j] = aff
        matrix[j, i] = aff

    n_nonzero = np.count_nonzero(matrix) // 2  # dibagi 2 karena matriks simetris

    metadata = {
        "w1": w1,
        "w2": w2,
        "n_rules": len(rules),
        "n_pairs_with_affinity": len(pair_support),
        "n_nonzero_cells": n_nonzero,
        "n_categories": n,
    }

    logger.info(
        "affinity matrix: %d kategori, %d pasangan skor > 0",
        n, n_nonzero,
    )

    return AffinityMatrix(
        matrix=matrix,
        categories=categories,
        rules=rules,
        metadata=metadata,
    )

def run_temporal_arm_pipeline(
    transactions: pd.DataFrame,
    binary_matrix: pd.DataFrame,
    categories: list[str],
    half_life_days: float = HALF_LIFE_DAYS,
    min_support: float = MIN_SUPPORT,
    min_confidence: float = MIN_CONFIDENCE,
    w1: float = W1,
    w2: float = W2,
) -> AffinityMatrix:
    """Pipeline ARM berbobot temporal (Approach A, weighted FP-Growth kustom).

    `transactions` harus memiliki kolom ``timestamp``.
    """
    logger.info("Temporal ARM: H=%s hari, support=%.3f, confidence=%.3f", half_life_days, min_support, min_confidence)

    weights = compute_temporal_weights(transactions["timestamp"], half_life_days)
    logger.info(
        "bobot temporal: min=%.6f, max=%.4f, mean=%.4f",
        weights.min(), weights.max(), weights.mean(),
    )

    freq, rules = run_weighted_arm_custom(
        binary_matrix, weights, min_support, min_confidence
    )
    logger.info("frequent itemsets: %d, aturan: %d", len(freq), len(rules))

    affinity = compute_affinity_matrix(rules, categories, w1, w2)
    affinity.metadata["approach"] = "A (weighted FP-Growth kustom)"
    affinity.metadata["half_life_days"] = half_life_days
    affinity.metadata["min_support"] = min_support
    affinity.metadata["min_confidence"] = min_confidence

    return affinity
