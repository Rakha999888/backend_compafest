"""Rekomendasi penempatan kategori pada grid gudang berdasarkan frekuensi dan sentralitas afinitas."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import pandas as pd

from ml.config import BETA
from ml.temporal_arm import AffinityMatrix
from ml.warehouse_simulation import WarehouseGrid, manhattan_distance

logger = logging.getLogger(__name__)

@dataclass
class SlottingResult:
    """Hasil rekomendasi slotting kategori ke posisi grid."""

    assignment: dict[str, tuple[int, int]]  # kategori -> (aisle, position)
    scores: dict[str, float]                # skor slotting per kategori
    frequency_scores: dict[str, float]      # frekuensi ternormalisasi
    centrality_scores: dict[str, float]     # sentralitas afinitas ternormalisasi
    metadata: dict[str, Any] = field(default_factory=dict)

def compute_frequency_scores(
    transactions: pd.DataFrame,
    categories: list[str],
) -> dict[str, float]:
    """Hitung frekuensi ternormalisasi (min-max) per kategori."""
    freq: dict[str, int] = {c: 0 for c in categories}
    for itemset in transactions["itemset"]:
        for item in itemset:
            if item in freq:
                freq[item] += 1

    values = list(freq.values())
    v_min, v_max = min(values), max(values)
    if v_max - v_min < 1e-12:
        return {c: 0.5 for c in categories}

    return {
        c: (freq[c] - v_min) / (v_max - v_min)
        for c in categories
    }

def compute_centrality_scores(
    affinity: AffinityMatrix,
) -> dict[str, float]:
    """Hitung sentralitas afinitas ternormalisasi via networkx.

    Sentralitas = weighted degree dalam graf afinitas.
    """
    G = nx.Graph()
    cats = affinity.categories
    for i in range(len(cats)):
        G.add_node(cats[i])
        for j in range(i + 1, len(cats)):
            if affinity.matrix[i, j] > 0:
                G.add_edge(cats[i], cats[j], weight=affinity.matrix[i, j])

    weighted_degree = {}
    for node in cats:
        if node in G:
            weighted_degree[node] = sum(
                d.get("weight", 0) for _, _, d in G.edges(node, data=True)
            )
        else:
            weighted_degree[node] = 0.0

    values = list(weighted_degree.values())
    v_min, v_max = min(values), max(values)
    if v_max - v_min < 1e-12:
        return {c: 0.5 for c in cats}

    return {
        c: (weighted_degree[c] - v_min) / (v_max - v_min)
        for c in cats
    }

def compute_slotting_scores(
    frequency_scores: dict[str, float],
    centrality_scores: dict[str, float],
    beta: float = BETA,
) -> dict[str, float]:
    """Skor gabungan: beta * freq_norm + (1-beta) * centrality_norm."""
    categories = set(frequency_scores.keys()) | set(centrality_scores.keys())
    return {
        c: beta * frequency_scores.get(c, 0.0)
        + (1 - beta) * centrality_scores.get(c, 0.0)
        for c in categories
    }

def assign_categories_to_grid(
    scores: dict[str, float],
    affinity: AffinityMatrix,
    grid: WarehouseGrid,
) -> dict[str, tuple[int, int]]:
    """Tempatkan kategori ke grid: skor tinggi -> posisi dekat depot, skor rendah mengikuti afinitas."""
    sorted_cats = sorted(scores, key=scores.get, reverse=True)
    available = set(grid.all_positions())
    assignment: dict[str, tuple[int, int]] = {}

    for cat in sorted_cats:
        if not available:
            break

        if not assignment:
            best_pos = min(
                available,
                key=lambda p: manhattan_distance(p, grid.depot, grid),
            )
        else:
            best_pos = None
            best_score = float("inf")

            for pos in available:
                depot_dist = manhattan_distance(pos, grid.depot, grid)

                # Tarik afinitas: semakin dekat ke kategori berafinitas tinggi, semakin baik
                affinity_pull = 0.0
                for placed_cat, placed_pos in assignment.items():
                    aff = affinity.get_affinity(cat, placed_cat)
                    if aff > 0:
                        dist = manhattan_distance(pos, placed_pos, grid)
                        affinity_pull += aff * dist

                combined = depot_dist + affinity_pull
                if combined < best_score:
                    best_score = combined
                    best_pos = pos

        if best_pos is not None:
            assignment[cat] = best_pos
            available.discard(best_pos)

    return assignment

def run_slotting(
    transactions: pd.DataFrame,
    affinity: AffinityMatrix,
    grid: WarehouseGrid,
    beta: float = BETA,
) -> SlottingResult:
    """Pipeline lengkap rekomendasi slotting."""
    categories = affinity.categories

    logger.info("Slotting: %d kategori, beta=%.2f", len(categories), beta)

    freq_scores = compute_frequency_scores(transactions, categories)
    centrality_scores = compute_centrality_scores(affinity)
    slotting_scores = compute_slotting_scores(freq_scores, centrality_scores, beta)

    assignment = assign_categories_to_grid(slotting_scores, affinity, grid)

    sorted_scores = sorted(slotting_scores.items(), key=lambda x: x[1], reverse=True)
    logger.info("top-5 slotting:")
    for cat, score in sorted_scores[:5]:
        pos = assignment.get(cat, (-1, -1))
        dist = manhattan_distance(pos, grid.depot, grid) if cat in assignment else -1
        logger.info("%s: score=%.4f, pos=%s, dist_depot=%.1f", cat, score, pos, dist)

    return SlottingResult(
        assignment=assignment,
        scores=slotting_scores,
        frequency_scores=freq_scores,
        centrality_scores=centrality_scores,
        metadata={
            "beta": beta,
            "n_categories": len(categories),
            "n_assigned": len(assignment),
        },
    )
