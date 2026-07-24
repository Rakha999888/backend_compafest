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
            from app.services.ml_client import get_ml_client
            self.ml_client = get_ml_client()
            logger.info("Using MLClient (connecting to %s)", settings.ML_SERVICE_URL)

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

        distance_comparison = {
            "distance_random": ml_response.distance_comparison.distance_random,
            "distance_abc": ml_response.distance_comparison.distance_abc,
            "distance_system": ml_response.distance_comparison.distance_system,
            "savings_vs_random_pct": ml_response.distance_comparison.savings_vs_random_pct,
            "savings_vs_abc_pct": ml_response.distance_comparison.savings_vs_abc_pct,
        }

        metadata = {}
        if ml_response.metadata:
            metadata = {
                "n_orders": ml_response.metadata.n_orders,
                "n_categories": ml_response.metadata.n_categories,
                "n_batches": ml_response.metadata.n_batches,
                "total_distance": ml_response.metadata.total_distance,
                "timings": ml_response.metadata.timings.model_dump(exclude_none=True) if ml_response.metadata.timings else None,
                "disclaimer": ml_response.metadata.disclaimer,
            }

        if ml_response.summary:
            metadata["summary"] = ml_response.summary.model_dump(exclude_none=True)

        return {
            "success": True,
            "message": "Recommendation generated successfully",
            "data": {
                "slotting_map": slotting_map,
                "batches": batches,
                "distance_comparison": distance_comparison,
                "metadata": metadata,
            },
        }


def get_recommend_service() -> RecommendService:
    return RecommendService()