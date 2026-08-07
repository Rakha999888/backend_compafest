"""API layer untuk konfigurasi gudang dan inferensi per request."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from ml.config import (
    AISLE_WIDTH,
    DEPOT_POSITION,
    N_AISLES,
    N_POSITIONS_PER_AISLE,
    POPULATION_SIZE,
    POSITION_SPACING,
    RANDOM_SEED,
)
from ml.genetic_batching import (
    Order,
    run_ga_batching,
)
from ml.pipeline import compute_distance_comparison
from ml.preprocessing import PreprocessedData
from ml.routing import compute_batch_routes, summarize_routes
from ml.slotting import SlottingResult, run_slotting
from ml.temporal_arm import AffinityMatrix
from ml.warehouse_simulation import WarehouseGrid

logger = logging.getLogger(__name__)

@dataclass
class WarehouseConfig:
    """Konfigurasi dimensi gudang dari user."""

    n_aisles: int = N_AISLES
    n_positions_per_aisle: int = N_POSITIONS_PER_AISLE
    aisle_width: float = AISLE_WIDTH
    position_spacing: float = POSITION_SPACING
    depot: tuple[int, int] = DEPOT_POSITION

    @property
    def total_positions(self) -> int:
        return self.n_aisles * self.n_positions_per_aisle

@dataclass
class ValidationMessage:
    """Satu pesan validasi konfigurasi gudang."""

    level: str
    code: str
    message: str

@dataclass
class ValidationResult:
    """Hasil validasi konfigurasi gudang."""

    valid: bool
    messages: list[ValidationMessage] = field(default_factory=list)

@dataclass
class WarehouseConfigResult:
    """Hasil konfigurasi gudang."""

    config: WarehouseConfig
    grid: WarehouseGrid
    slotting: SlottingResult
    slotting_map: dict[str, dict[str, int]]  # kategori -> {aisle, position}
    validation: ValidationResult
    n_categories: int
    time_s: float

@dataclass
class InferenceResult:
    """Hasil inferensi per request."""

    batches: list[dict[str, Any]]
    distance_comparison: dict[str, Any]
    slotting_map: dict[str, dict[str, int]]
    summary: dict[str, Any]

def get_default_warehouse_config() -> WarehouseConfig:
    """Mengembalikan konfigurasi gudang default dari config.py."""
    return WarehouseConfig()

def validate_warehouse_config(
    config: WarehouseConfig,
    n_categories: int,
) -> ValidationResult:
    """Validasi konfigurasi gudang."""
    messages: list[ValidationMessage] = []

    if config.n_aisles < 1:
        messages.append(ValidationMessage(
            "error", "INVALID_AISLES",
            f"Jumlah lorong harus >= 1, diterima: {config.n_aisles}",
        ))

    if config.n_positions_per_aisle < 1:
        messages.append(ValidationMessage(
            "error", "INVALID_POSITIONS",
            f"Jumlah posisi per lorong harus >= 1, diterima: {config.n_positions_per_aisle}",
        ))

    if config.aisle_width <= 0:
        messages.append(ValidationMessage(
            "error", "INVALID_AISLE_WIDTH",
            f"Lebar lorong harus > 0, diterima: {config.aisle_width}",
        ))

    if config.position_spacing <= 0:
        messages.append(ValidationMessage(
            "error", "INVALID_SPACING",
            f"Jarak antar posisi harus > 0, diterima: {config.position_spacing}",
        ))

    if config.total_positions < n_categories:
        messages.append(ValidationMessage(
            "error", "GRID_TOO_SMALL",
            f"Kapasitas grid ({config.total_positions} slot) kurang dari "
            f"jumlah kategori ({n_categories}). Minimal: {n_categories} slot.",
        ))

    depot_a, depot_p = config.depot
    if config.n_aisles >= 1 and config.n_positions_per_aisle >= 1:
        if not (0 <= depot_a < config.n_aisles
                and 0 <= depot_p < config.n_positions_per_aisle):
            messages.append(ValidationMessage(
                "error", "INVALID_DEPOT",
                f"Posisi depot {config.depot} di luar grid "
                f"({config.n_aisles} x {config.n_positions_per_aisle}).",
            ))

    if config.n_aisles > 50:
        messages.append(ValidationMessage(
            "warning", "LARGE_AISLES",
            f"Jumlah lorong ({config.n_aisles}) sangat besar. Sesuai dengan gudang Anda?",
        ))

    if config.n_positions_per_aisle > 50:
        messages.append(ValidationMessage(
            "warning", "LARGE_POSITIONS",
            f"Jumlah posisi per lorong ({config.n_positions_per_aisle}) sangat besar. Sesuai?",
        ))

    if config.total_positions > 5 * n_categories and n_categories > 0:
        messages.append(ValidationMessage(
            "warning", "SPARSE_GRID",
            f"Grid sangat sparse: {config.total_positions} slot untuk "
            f"{n_categories} kategori. Banyak posisi akan kosong.",
        ))

    has_error = any(m.level == "error" for m in messages)
    return ValidationResult(valid=not has_error, messages=messages)

def configure_warehouse(
    train_data: PreprocessedData,
    affinity: AffinityMatrix,
    config: WarehouseConfig | None = None,
) -> WarehouseConfigResult:
    """Konfigurasi gudang dan hitung slotting, raises ValueError jika config tidak valid."""
    if config is None:
        config = get_default_warehouse_config()
        logger.info("konfigurasi gudang default: %s", config)

    n_categories = len(train_data.binary_matrix.columns)

    validation = validate_warehouse_config(config, n_categories)
    if not validation.valid:
        error_msgs = [
            m.message for m in validation.messages if m.level == "error"
        ]
        raise ValueError(
            "Konfigurasi gudang tidak valid:\n"
            + "\n".join(f"  - {e}" for e in error_msgs)
        )

    for msg in validation.messages:
        if msg.level == "warning":
            logger.warning("%s", msg.message)

    logger.info(
        "konfigurasi gudang: %d lorong x %d posisi = %d slot",
        config.n_aisles, config.n_positions_per_aisle, config.total_positions,
    )

    t_start = time.time()

    grid = WarehouseGrid(
        n_aisles=config.n_aisles,
        n_positions_per_aisle=config.n_positions_per_aisle,
        aisle_width=config.aisle_width,
        position_spacing=config.position_spacing,
        depot=config.depot,
    )
    slotting = run_slotting(train_data.transactions, affinity, grid)

    elapsed = time.time() - t_start

    slotting_map = {
        cat: {"aisle": pos[0], "position": pos[1]}
        for cat, pos in slotting.assignment.items()
    }

    logger.info(
        "slotting selesai: %d kategori ditempatkan, %.3fs",
        len(slotting_map), elapsed,
    )

    return WarehouseConfigResult(
        config=config,
        grid=grid,
        slotting=slotting,
        slotting_map=slotting_map,
        validation=validation,
        n_categories=len(slotting_map),
        time_s=round(elapsed, 3),
    )

def infer(
    orders: list[dict[str, Any]],
    affinity: AffinityMatrix,
    slotting: SlottingResult,
    grid: WarehouseGrid,
    categories: list[str],
    frequencies: dict[str, int],
    seed: int = RANDOM_SEED,
) -> InferenceResult:
    """GA batching + routing per request, raises ValueError jika orders kosong atau format invalid."""
    if not orders:
        raise ValueError("Daftar orders kosong.")

    for i, o in enumerate(orders):
        if "order_id" not in o:
            raise ValueError(f"Order index {i} tidak memiliki 'order_id'.")
        if "categories" not in o or not o["categories"]:
            raise ValueError(
                f"Order '{o.get('order_id', i)}' tidak memiliki "
                f"'categories' atau categories kosong."
            )

    known = set(categories)
    unknown_cats = set()
    for o in orders:
        for cat in o["categories"]:
            if cat not in known:
                unknown_cats.add(cat)

    if unknown_cats:
        logger.warning(
            "kategori tidak dikenali (diabaikan): %s",
            sorted(unknown_cats),
        )

    t_start = time.time()

    order_objects = [
        Order(order_id=o["order_id"], categories=o["categories"])
        for o in orders
    ]

    batching = run_ga_batching(
        order_objects, affinity,
        population_size=POPULATION_SIZE, seed=seed,
    )

    order_map = {o.order_id: o for o in order_objects}
    batch_locations_list = []
    for batch_order_ids in batching.batches:
        locs = []
        for oid in batch_order_ids:
            if oid in order_map:
                for cat in order_map[oid].categories:
                    if cat in slotting.assignment:
                        loc = slotting.assignment[cat]
                        if loc not in locs:
                            locs.append(loc)
        batch_locations_list.append(locs)

    routes = compute_batch_routes(batch_locations_list, grid)
    route_summary = summarize_routes(routes)

    comparison = compute_distance_comparison(
        batching, order_objects, slotting.assignment,
        grid, categories, frequencies,
    )

    elapsed = time.time() - t_start

    formatted_batches = []
    for i, batch_ids in enumerate(batching.batches):
        batch_data = {
            "batch_id": i,
            "order_ids": batch_ids,
            "picking_route": {
                "sequence": [
                    {"aisle": loc[0], "position": loc[1]}
                    for loc in routes[i].route
                ] if i < len(routes) else [],
                "distance": (
                    routes[i].total_distance if i < len(routes) else 0
                ),
                "heuristic": (
                    routes[i].heuristic if i < len(routes) else "none"
                ),
            },
        }
        formatted_batches.append(batch_data)

    slotting_map = {
        cat: {"aisle": pos[0], "position": pos[1]}
        for cat, pos in slotting.assignment.items()
    }

    summary = {
        "n_orders": len(orders),
        "n_batches": batching.n_batches,
        "total_distance": route_summary.get("total_distance", 0),
        "best_fitness": round(batching.best_fitness, 4),
        "inference_time_s": round(elapsed, 3),
        "unknown_categories": sorted(unknown_cats) if unknown_cats else [],
        "disclaimer": (
            "Estimasi simulatif berdasarkan grid gudang sintetis "
            "dan Manhattan distance, bukan pengukuran picker riil."
        ),
    }

    return InferenceResult(
        batches=formatted_batches,
        distance_comparison=comparison,
        slotting_map=slotting_map,
        summary=summary,
    )
