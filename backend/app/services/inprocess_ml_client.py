"""
InProcessMLClient — adapter yang bikin RecommendService langsung pakai
MLService (in-process) alih-alih connect ke ML service eksternal.

ML sudah di-train dari CSV saat startup via lifespan di main.py.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from fastapi import Request

from app.schemas.ml import (
    MLResponse,
    MLInferenceRequest,
    MLFullPipelineRequest,
    Coordinate,
    BatchResponse,
    PickingRoute,
    DistanceComparison,
    MLMetadata,
    MLTimings,
    MLInferenceSummary,
)
from app.services.ml_client import MLClientError
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)


class InProcessMLClient:
    """ML client yang langsung panggil MLService in-process (no HTTP)."""

    def __init__(self, ml_state, ml_service: MLService | None = None):
        self._state = ml_state
        self._service = ml_service or MLService()

    def _ensure_trained(self) -> None:
        if self._state.is_training:
            raise MLClientError(
                error_code="STILL_TRAINING",
                message="Model sedang di-train, coba lagi beberapa saat.",
            )
        if not self._state.is_trained:
            raise MLClientError(
                error_code="NOT_TRAINED",
                message="Model belum di-train. Restart server atau panggil POST /api/ml/train.",
            )

    def _ensure_configured(self) -> None:
        if not self._state.is_configured:
            logger.info("Warehouse belum dikonfigurasi, auto-configure dengan default...")
            self._service.configure_warehouse(self._state, {})

    async def infer(self, request: MLInferenceRequest) -> MLResponse:
        self._ensure_trained()
        self._ensure_configured()

        orders = [
            {"order_id": o.order_id, "categories": o.categories}
            for o in request.orders
        ]

        try:
            result = await asyncio.to_thread(
                self._service.infer, self._state, orders, request.seed
            )
        except ValueError as exc:
            raise MLClientError(
                error_code="INFERENCE_FAILED",
                message=str(exc),
            )

        return self._to_ml_response(result)

    async def full_pipeline(self, request: MLFullPipelineRequest) -> MLResponse:
        self._ensure_trained()
        self._ensure_configured()

        orders = self._load_orders_from_source(request.data_source, request.max_orders)

        if not orders:
            raise MLClientError(
                error_code="EMPTY_ORDERS",
                message=f"Tidak ada orders dari data source: {request.data_source}",
            )

        try:
            result = await asyncio.to_thread(
                self._service.infer, self._state, orders, request.seed
            )
        except ValueError as exc:
            raise MLClientError(
                error_code="INFERENCE_FAILED",
                message=str(exc),
            )

        return self._to_ml_response(result)

    def _load_orders_from_source(
        self, data_source: str, max_orders: Optional[int] = None
    ) -> list[dict]:
        
        cached = self._state.cached_orders
        if not cached:
            raise MLClientError(
                error_code="NO_CACHED_DATA",
                message="Data orders belum tersedia. Training mungkin belum selesai.",
            )

        
        size_limits = {
            "small": 200,
            "medium": 1000,
            "large": 3000,
        }
        effective_max = max_orders or size_limits.get(data_source)

        orders = cached
        if effective_max and len(orders) > effective_max:
            orders = orders[:effective_max]

        logger.info(
            "Loaded %d orders dari cache (data_source=%s, total_cached=%d)",
            len(orders), data_source, len(cached),
        )
        return orders

    def _to_ml_response(self, result: dict) -> MLResponse:
        """Convert InferenceResult dict -> MLResponse schema."""
        slotting_map = {
            cat: Coordinate(aisle=coord["aisle"], position=coord["position"])
            for cat, coord in result.get("slotting_map", {}).items()
        }

        batches = []
        for b in result.get("batches", []):
            route = b.get("picking_route", {})
            seq = [
                Coordinate(aisle=s["aisle"], position=s["position"])
                for s in route.get("sequence", [])
            ]
            batches.append(
                BatchResponse(
                    batch_id=b["batch_id"],
                    order_ids=b["order_ids"],
                    picking_route=PickingRoute(
                        sequence=seq,
                        distance=route.get("distance", 0),
                        heuristic=route.get("heuristic", "none"),
                    ),
                )
            )

        dc = result.get("distance_comparison", {})
        distance_comparison = DistanceComparison(
            distance_random=dc.get("distance_random", 0),
            distance_abc=dc.get("distance_abc", 0),
            distance_system=dc.get("distance_system", 0),
            savings_vs_random_pct=dc.get("savings_vs_random_pct", 0),
            savings_vs_abc_pct=dc.get("savings_vs_abc_pct", 0),
        )

        summary_data = result.get("summary", {})
        summary = MLInferenceSummary(
            n_orders=summary_data.get("n_orders"),
            n_batches=summary_data.get("n_batches"),
            total_distance=summary_data.get("total_distance"),
            best_fitness=summary_data.get("best_fitness"),
            inference_time_s=summary_data.get("inference_time_s"),
        )

        metadata = MLMetadata(
            n_orders=summary_data.get("n_orders"),
            n_categories=len(slotting_map),
            n_batches=summary_data.get("n_batches"),
            total_distance=summary_data.get("total_distance"),
            disclaimer=summary_data.get("disclaimer"),
        )

        return MLResponse(
            slotting_map=slotting_map,
            batches=batches,
            distance_comparison=distance_comparison,
            metadata=metadata,
            summary=summary,
        )
