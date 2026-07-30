from typing import Dict, List
import logging
from datetime import datetime

from app.repositories.order_repository import OrderRepository
from app.adapters.ml_adapter import MLAdapter


logger = logging.getLogger(__name__)


class RecommendationService:
    
    def __init__(self, order_repo: OrderRepository, ml_adapter: MLAdapter):
        self.order_repo = order_repo
        self.ml_adapter = ml_adapter
    
    def recommend(self, order_ids: List[str]) -> Dict:
        
        logger.info(f"Starting recommendation for {len(order_ids)} orders")
        
        orders = self.order_repo.get_orders_with_categories(order_ids)
        
        if not orders:
            logger.warning("No orders found for the given IDs")
            return {
                "error": "No orders found",
                "order_ids": order_ids,
                "generated_at": datetime.now().isoformat()
            }
        
        logger.info(f"Fetched {len(orders)} orders with categories")
        
        ml_result = self.ml_adapter.run(orders)
        
        ml_result["generated_at"] = datetime.now().isoformat()
        ml_result["requested_order_ids"] = order_ids
        ml_result["processed_order_count"] = len(orders)
        
        logger.info(
            f"Recommendation complete: "
            f"{ml_result['metadata']['total_batches']} batches, "
            f"{ml_result['metadata']['total_distance']} total distance"
        )
        
        return ml_result


def get_recommendation_service() -> RecommendationService:
    order_repo = OrderRepository(data_source="demo")
    ml_adapter = MLAdapter()
    return RecommendationService(order_repo, ml_adapter)