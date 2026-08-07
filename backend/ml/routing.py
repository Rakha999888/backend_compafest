"""Heuristik routing picking per batch: S-shape, largest gap, dan composite."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ml.warehouse_simulation import WarehouseGrid, manhattan_distance

@dataclass
class PickingRoute:
    """Hasil rute picking untuk satu batch."""

    route: list[tuple[int, int]]   # urutan lokasi dikunjungi (tanpa depot)
    total_distance: float          # total jarak termasuk dari dan ke depot
    heuristic: str
    metadata: dict[str, Any] = field(default_factory=dict)

def s_shape_route(
    locations: list[tuple[int, int]],
    grid: WarehouseGrid,
) -> PickingRoute:
    """S-shape: picker melewati lorong berurutan dengan pola serpentine, lorong kosong dilewati."""
    if not locations:
        return PickingRoute([], 0.0, "s_shape")

    aisle_items: dict[int, list[int]] = {}
    for aisle, pos in locations:
        if aisle not in aisle_items:
            aisle_items[aisle] = []
        aisle_items[aisle].append(pos)

    sorted_aisles = sorted(aisle_items.keys())
    route = []
    going_up = True

    for aisle in sorted_aisles:
        positions = sorted(aisle_items[aisle])
        if going_up:
            for pos in positions:
                route.append((aisle, pos))
        else:
            for pos in reversed(positions):
                route.append((aisle, pos))
        going_up = not going_up

    total_dist = _compute_route_distance(route, grid)

    return PickingRoute(
        route=route,
        total_distance=total_dist,
        heuristic="s_shape",
        metadata={"n_aisles_visited": len(sorted_aisles)},
    )

def largest_gap_route(
    locations: list[tuple[int, int]],
    grid: WarehouseGrid,
) -> PickingRoute:
    """Largest gap: picker berbalik di titik gap terbesar antar item pada setiap lorong."""
    if not locations:
        return PickingRoute([], 0.0, "largest_gap")

    aisle_items: dict[int, list[int]] = {}
    for aisle, pos in locations:
        if aisle not in aisle_items:
            aisle_items[aisle] = []
        aisle_items[aisle].append(pos)

    sorted_aisles = sorted(aisle_items.keys())
    route = []

    for aisle in sorted_aisles:
        positions = sorted(aisle_items[aisle])

        if len(positions) == 1:
            route.append((aisle, positions[0]))
            continue

        # Hitung gap: dari batas bawah, antar item, dan ke batas atas
        gaps = [(0, positions[0], positions[0])]
        for k in range(len(positions) - 1):
            gap_size = positions[k + 1] - positions[k]
            gaps.append((positions[k], positions[k + 1], gap_size))
        top = grid.n_positions_per_aisle - 1
        gaps.append((positions[-1], top, top - positions[-1]))

        largest = max(gaps, key=lambda g: g[2])

        below_gap = [p for p in positions if p <= largest[0]]
        above_gap = [p for p in positions if p >= largest[1]]

        for p in sorted(below_gap):
            route.append((aisle, p))
        for p in sorted(above_gap, reverse=True):
            if (aisle, p) not in route:
                route.append((aisle, p))

    total_dist = _compute_route_distance(route, grid)

    return PickingRoute(
        route=route,
        total_distance=total_dist,
        heuristic="largest_gap",
        metadata={"n_aisles_visited": len(sorted_aisles)},
    )

def composite_route(
    locations: list[tuple[int, int]],
    grid: WarehouseGrid,
) -> PickingRoute:
    """S-shape dan largest gap, pilih yang jarak lebih pendek."""
    if not locations:
        return PickingRoute([], 0.0, "composite")

    route_s = s_shape_route(locations, grid)
    route_lg = largest_gap_route(locations, grid)

    if route_s.total_distance <= route_lg.total_distance:
        best = route_s
        best.heuristic = "composite_s_shape"
    else:
        best = route_lg
        best.heuristic = "composite_largest_gap"

    best.metadata["s_shape_distance"] = route_s.total_distance
    best.metadata["largest_gap_distance"] = route_lg.total_distance
    best.metadata["savings_vs_worse"] = abs(
        route_s.total_distance - route_lg.total_distance
    )

    return best

def _compute_route_distance(
    route: list[tuple[int, int]],
    grid: WarehouseGrid,
) -> float:
    """Hitung total jarak rute (depot -> lokasi... -> depot)."""
    if not route:
        return 0.0

    dist = manhattan_distance(grid.depot, route[0], grid)
    for i in range(len(route) - 1):
        dist += manhattan_distance(route[i], route[i + 1], grid)
    dist += manhattan_distance(route[-1], grid.depot, grid)
    return dist

def compute_batch_routes(
    batches: list[list[tuple[int, int]]],
    grid: WarehouseGrid,
) -> list[PickingRoute]:
    """Hitung rute picking untuk setiap batch."""
    return [composite_route(batch_locs, grid) for batch_locs in batches]

def summarize_routes(routes: list[PickingRoute]) -> dict[str, Any]:
    """Ringkasan statistik rute picking."""
    if not routes:
        return {"total_distance": 0, "n_batches": 0}

    distances = [r.total_distance for r in routes]
    heuristics = [r.heuristic for r in routes]

    return {
        "total_distance": sum(distances),
        "avg_distance_per_batch": sum(distances) / len(distances),
        "min_distance": min(distances),
        "max_distance": max(distances),
        "n_batches": len(routes),
        "heuristic_counts": {
            h: heuristics.count(h) for h in set(heuristics)
        },
    }
