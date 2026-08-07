"""Model grid gudang sintetis untuk estimasi jarak tempuh picking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ml.config import (
    AISLE_WIDTH,
    DEPOT_POSITION,
    N_AISLES,
    N_POSITIONS_PER_AISLE,
    POSITION_SPACING,
    RANDOM_SEED,
)

@dataclass
class WarehouseGrid:
    """Grid gudang single-block dengan lorong paralel.

    Koordinat: (aisle_index, position_index), depot default di (0, 0).
    Jarak fisik: antar lorong = aisle_width, antar posisi = position_spacing.
    """

    n_aisles: int = N_AISLES
    n_positions_per_aisle: int = N_POSITIONS_PER_AISLE
    depot: tuple[int, int] = DEPOT_POSITION
    aisle_width: float = AISLE_WIDTH
    position_spacing: float = POSITION_SPACING

    @property
    def total_positions(self) -> int:
        """Jumlah total posisi penyimpanan pada grid."""
        return self.n_aisles * self.n_positions_per_aisle

    def is_valid_location(self, loc: tuple[int, int]) -> bool:
        """Periksa apakah lokasi valid pada grid."""
        a, p = loc
        return 0 <= a < self.n_aisles and 0 <= p < self.n_positions_per_aisle

    def all_positions(self) -> list[tuple[int, int]]:
        """Daftar seluruh posisi penyimpanan pada grid."""
        return [
            (a, p)
            for a in range(self.n_aisles)
            for p in range(self.n_positions_per_aisle)
        ]

def manhattan_distance(
    loc_a: tuple[int, int],
    loc_b: tuple[int, int],
    grid: WarehouseGrid,
) -> float:
    """Jarak rectilinear antara dua lokasi, menggunakan aisle_width dan position_spacing."""
    aisle_diff = abs(loc_a[0] - loc_b[0]) * grid.aisle_width
    pos_diff = abs(loc_a[1] - loc_b[1]) * grid.position_spacing
    return aisle_diff + pos_diff

def total_route_distance(
    route: list[tuple[int, int]],
    grid: WarehouseGrid,
) -> float:
    """Total jarak rute depot → lokasi... → depot."""
    if not route:
        return 0.0

    distance = manhattan_distance(grid.depot, route[0], grid)
    for i in range(len(route) - 1):
        distance += manhattan_distance(route[i], route[i + 1], grid)
    distance += manhattan_distance(route[-1], grid.depot, grid)
    return distance

def create_random_assignment(
    categories: list[str],
    grid: WarehouseGrid,
    seed: int = RANDOM_SEED,
) -> dict[str, tuple[int, int]]:
    """Baseline acak: tempatkan kategori secara random pada grid.

    Raises ValueError jika jumlah kategori melebihi kapasitas grid.
    """
    if len(categories) > grid.total_positions:
        raise ValueError(
            f"Jumlah kategori ({len(categories)}) melebihi "
            f"kapasitas grid ({grid.total_positions})"
        )

    rng = np.random.default_rng(seed)
    positions = grid.all_positions()
    selected = rng.choice(len(positions), size=len(categories), replace=False)
    return {cat: positions[i] for cat, i in zip(categories, selected)}

def create_abc_assignment(
    categories: list[str],
    frequencies: dict[str, float],
    grid: WarehouseGrid,
) -> dict[str, tuple[int, int]]:
    """Baseline ABC: tempatkan kategori berdasarkan frekuensi descending ke posisi terdekat depot.

    Raises ValueError jika jumlah kategori melebihi kapasitas grid.
    """
    if len(categories) > grid.total_positions:
        raise ValueError(
            f"Jumlah kategori ({len(categories)}) melebihi "
            f"kapasitas grid ({grid.total_positions})"
        )

    sorted_cats = sorted(
        categories,
        key=lambda c: frequencies.get(c, 0),
        reverse=True,
    )

    positions = grid.all_positions()
    positions_sorted = sorted(
        positions,
        key=lambda pos: manhattan_distance(pos, grid.depot, grid),
    )

    return {
        cat: positions_sorted[i] for i, cat in enumerate(sorted_cats)
    }

def compute_category_frequencies(
    transactions: pd.DataFrame,
) -> dict[str, int]:
    """Hitung frekuensi kemunculan setiap kategori dalam kolom itemset."""
    freq: dict[str, int] = {}
    for itemset in transactions["itemset"]:
        for item in itemset:
            freq[item] = freq.get(item, 0) + 1
    return freq

def simulate_picking_distance(
    orders: list[list[str]],
    assignment: dict[str, tuple[int, int]],
    grid: WarehouseGrid,
) -> dict[str, Any]:
    """Simulasi jarak picking per order secara individual (tanpa batching)."""
    distances = []
    for order in orders:
        locations = [assignment[cat] for cat in order if cat in assignment]
        if locations:
            dist = total_route_distance(locations, grid)
            distances.append(dist)
        else:
            distances.append(0.0)

    total = sum(distances)
    avg = total / len(distances) if distances else 0.0

    return {
        "total_distance": total,
        "avg_distance_per_order": avg,
        "n_orders": len(orders),
        "distances": distances,
    }
