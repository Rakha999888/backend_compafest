import logging
from typing import Dict, Any, List, Optional
from app.config.settings import settings
from app.schemas.ml import (
    MLInferenceRequest,
    MLInferenceOrder,
    MLFullPipelineRequest,
    MLResponse,
)
from app.utils.exceptions import MLServiceError

logger = logging.getLogger(__name__)


class RecommendService:
    def __init__(self, ml_client=None):
        if ml_client is not None:
            self.ml_client = ml_client
        elif settings.USE_MOCK_ML:
            from app.services.mock_ml_client import get_mock_ml_client
            self.ml_client = get_mock_ml_client()
            logger.info("Using MockMLClient (reading from ML/ JSON files)")
        else:
            from app.services.inprocess_ml_client import InProcessMLClient
            from app.services.ml_service import MLService
            from app.core.ml_state import MLState

            import app.main as _main_mod
            _app = getattr(_main_mod, '_app_instance', None)
            if _app and hasattr(_app.state, 'ml_state'):
                ml_state = _app.state.ml_state
            else:
                ml_state = MLState()
                MLService().train(ml_state)

            self.ml_client = InProcessMLClient(ml_state)
            logger.info("Using InProcessMLClient (in-process ML, trained from CSV)")

    async def recommend(
        self,
        orders: List[Dict[str, Any]],
        seed: int = 42,
    ) -> Dict[str, Any]:
        from app.services.ml_client import MLClientError

        ml_orders = []
        for order in orders:
            order_id = order.get("order_id", "")
            categories = order.get("categories", [])
            if not order_id or not categories:
                continue
            ml_orders.append(MLInferenceOrder(
                order_id=order_id,
                categories=categories,
            ))

        if not ml_orders:
            raise MLServiceError(
                error_code="EMPTY_ORDERS",
                message="No valid orders provided",
            )

        request = MLInferenceRequest(orders=ml_orders, seed=seed)

        try:
            ml_response = await self.ml_client.infer(request)
        except MLClientError as exc:
            raise MLServiceError(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            )

        return self._format_response(ml_response)

    async def full_pipeline(
        self,
        data_source: str,
        max_orders: Optional[int] = None,
        seed: int = 42,
    ) -> Dict[str, Any]:
        from app.services.ml_client import MLClientError

        request = MLFullPipelineRequest(
            data_source=data_source,
            max_orders=max_orders,
            seed=seed,
        )

        try:
            ml_response = await self.ml_client.full_pipeline(request)
        except MLClientError as exc:
            raise MLServiceError(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
            )

        return self._format_response(ml_response)

    def _format_response(self, ml_response: MLResponse) -> Dict[str, Any]:
        slotting_map = {
            category: {"aisle": coord.aisle, "position": coord.position}
            for category, coord in ml_response.slotting_map.items()
        }

        batches = []
        for batch in ml_response.batches:
            batches.append({
                "batch_id": batch.batch_id,
                "order_ids": batch.order_ids,
                "picking_route": {
                    "sequence": [
                        {"aisle": s.aisle, "position": s.position}
                        for s in batch.picking_route.sequence
                    ],
                    "distance": batch.picking_route.distance,
                    "heuristic": batch.picking_route.heuristic,
                },
            })

        dc = ml_response.distance_comparison
        distance_comparison = {
            "baseline_random": dc.distance_random,
            "baseline_abc": dc.distance_abc,
            "optimized": dc.distance_system,
            "improvement_vs_random": dc.savings_vs_random_pct,
            "improvement_vs_abc": dc.savings_vs_abc_pct,
        }

        md = ml_response.metadata
        total_categories = len(slotting_map)
        total_orders = md.n_orders if md and md.n_orders else sum(len(b["order_ids"]) for b in batches)
        total_batches = md.n_batches if md and md.n_batches else len(batches)
        total_distance = md.total_distance if md and md.total_distance else sum(b["picking_route"]["distance"] for b in batches)

        metadata = {
            "total_orders": total_orders,
            "total_categories": total_categories,
            "total_batches": total_batches,
            "total_distance": total_distance,
            "min_support_used": 0.3,
            "min_confidence_used": 0.7,
            "frequent_itemsets_count": 0,
            "rules_count": 0,
        }

        if md and md.timings:
            metadata["timings"] = md.timings.model_dump(exclude_none=True)
        if md and md.disclaimer:
            metadata["disclaimer"] = md.disclaimer

        all_order_ids = []
        for batch in batches:
            all_order_ids.extend(batch["order_ids"])

        from datetime import datetime

        return {
            "success": True,
            "message": "Recommendation generated successfully",
            "data": {
                "slotting_map": slotting_map,
                "batches": batches,
                "distance_comparison": distance_comparison,
                "metadata": metadata,
                "generated_at": datetime.now().isoformat(),
                "requested_order_ids": all_order_ids,
                "processed_order_count": total_orders,
            },
        }


def get_recommend_service() -> RecommendService:
    return RecommendService()