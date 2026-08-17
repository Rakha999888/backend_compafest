"""Perbandingan jarak picking antara sistem (slotting+batching+routing) vs dua baseline."""

from __future__ import annotations

from typing import Any

from ml.genetic_batching import BatchingResult, Order
from ml.routing import composite_route
from ml.warehouse_simulation import (
    WarehouseGrid,
    create_abc_assignment,
    create_random_assignment,
    simulate_picking_distance,
)

def compute_distance_comparison(
    batching: BatchingResult,
    orders_data: list[Order],
    slotting_assignment: dict[str, tuple[int, int]],
    grid: WarehouseGrid,
    categories: list[str],
    frequencies: dict[str, int],
) -> dict[str, Any]:
    """Hitung jarak sistem vs baseline acak dan ABC, hasil berupa persentase penghematan."""
    order_map = {o.order_id: o for o in orders_data}
    all_orders_raw = [o.categories for o in orders_data]

    random_assign = create_random_assignment(categories, grid)
    random_result = simulate_picking_distance(all_orders_raw, random_assign, grid)
    dist_random = random_result["total_distance"]

    abc_assign = create_abc_assignment(categories, frequencies, grid)
    abc_result = simulate_picking_distance(all_orders_raw, abc_assign, grid)
    dist_abc = abc_result["total_distance"]

    dist_system = 0.0
    for batch_order_ids in batching.batches:
        batch_locations = []
        for oid in batch_order_ids:
            if oid in order_map:
                for cat in order_map[oid].categories:
                    if cat in slotting_assignment:
                        loc = slotting_assignment[cat]
                        if loc not in batch_locations:
                            batch_locations.append(loc)

        if batch_locations:
            route = composite_route(batch_locations, grid)
            dist_system += route.total_distance

    savings_vs_random = (
        (dist_random - dist_system) / dist_random * 100
        if dist_random > 0 else 0.0
    )
    savings_vs_abc = (
        (dist_abc - dist_system) / dist_abc * 100
        if dist_abc > 0 else 0.0
    )

    return {
        "distance_random": round(dist_random, 2),
        "distance_abc": round(dist_abc, 2),
        "distance_system": round(dist_system, 2),
        "savings_vs_random_pct": round(savings_vs_random, 2),
        "savings_vs_abc_pct": round(savings_vs_abc, 2),
        "n_orders": len(orders_data),
        "n_batches": batching.n_batches,
    }
