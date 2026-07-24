from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class Coordinate(BaseModel):
    aisle: int
    position: int


class SlotRecommendation(BaseModel):
    category: str
    aisle: int
    position: int


class PickingRoute(BaseModel):
    sequence: List[Coordinate]
    distance: float
    heuristic: str


class BatchResponse(BaseModel):
    batch_id: int
    order_ids: List[str]
    picking_route: PickingRoute


class DistanceComparison(BaseModel):
    distance_random: float
    distance_abc: float
    distance_system: float
    savings_vs_random_pct: float
    savings_vs_abc_pct: float


class MLTimings(BaseModel):
    preprocess: Optional[float] = None
    arm: Optional[float] = None
    ga_batching: Optional[float] = None
    routing_slotting: Optional[float] = None
    total: Optional[float] = None


class MLInferenceSummary(BaseModel):
    n_orders: Optional[int] = None
    n_batches: Optional[int] = None
    total_distance: Optional[float] = None
    best_fitness: Optional[float] = None
    inference_time_s: Optional[float] = None


class MLMetadata(BaseModel):
    n_orders: Optional[int] = None
    n_categories: Optional[int] = None
    n_batches: Optional[int] = None
    total_distance: Optional[float] = None
    timings: Optional[MLTimings] = None
    disclaimer: Optional[str] = None


class MLResponse(BaseModel):
    slotting_map: Dict[str, Coordinate]
    batches: List[BatchResponse]
    distance_comparison: DistanceComparison
    metadata: Optional[MLMetadata] = None
    summary: Optional[MLInferenceSummary] = None


class MLInferenceOrder(BaseModel):
    order_id: str
    categories: List[str] = Field(min_items=1)


class MLInferenceRequest(BaseModel):
    mode: str = "inference"
    orders: List[MLInferenceOrder] = Field(min_items=1)
    seed: Optional[int] = 42


class MLFullPipelineRequest(BaseModel):
    mode: str = "full_pipeline"
    data_source: str
    max_orders: Optional[int] = None
    seed: Optional[int] = 42


class MLErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict] = None