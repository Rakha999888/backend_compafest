from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class CoordinateDTO(BaseModel):
    aisle: int
    position: int


class PickingRouteDTO(BaseModel):
    sequence: List[CoordinateDTO]
    distance: float
    heuristic: str


class BatchDTO(BaseModel):
    batch_id: int
    order_ids: List[str]
    picking_route: PickingRouteDTO


class DistanceComparisonDTO(BaseModel):
    baseline_random: float
    baseline_abc: float
    optimized: float
    improvement_vs_random: float
    improvement_vs_abc: float


class RecommendationMetadataDTO(BaseModel):
    total_orders: int
    total_categories: int
    total_batches: int
    total_distance: float
    min_support_used: float
    min_confidence_used: float
    frequent_itemsets_count: int
    rules_count: int


class RecommendationDataDTO(BaseModel):
    slotting_map: Dict[str, CoordinateDTO]
    batches: List[BatchDTO]
    distance_comparison: DistanceComparisonDTO
    metadata: RecommendationMetadataDTO
    generated_at: str
    requested_order_ids: List[str]
    processed_order_count: int


class RecommendRequest(BaseModel):
    order_ids: Optional[List[str]] = Field(default=None, min_items=1)
    dataset: Optional[str] = None


class RecommendResponse(BaseModel):
    success: bool
    message: str
    data: Optional[RecommendationDataDTO] = None
    error: Optional[str] = None