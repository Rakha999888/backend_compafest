from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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
    categories: List[str] = Field(min_length=1)


class MLInferenceRequest(BaseModel):
    mode: str = "inference"
    orders: List[MLInferenceOrder] = Field(min_length=1)
    seed: Optional[int] = 42


class MLFullPipelineRequest(BaseModel):
    mode: str = "full_pipeline"
    data_source: str
    max_orders: Optional[int] = None
    seed: Optional[int] = 42


class TrainResponse(BaseModel):
    status: str
    n_categories: int
    n_rules: int
    n_transactions_train: int
    time_s: float


class WarehouseConfigRequest(BaseModel):
    """Semua field opsional, kalau body kosong {} pakai default dari config.py."""

    n_aisles: Optional[int] = Field(default=None, ge=1)
    n_positions_per_aisle: Optional[int] = Field(default=None, ge=1)
    aisle_width: Optional[float] = Field(default=None, gt=0)
    position_spacing: Optional[float] = Field(default=None, gt=0)
    depot: Optional[list[int]] = Field(default=None, min_length=2, max_length=2)


class WarehouseConfigResponse(BaseModel):
    config: dict[str, Any]
    slotting_map: dict[str, dict[str, int]]
    warnings: list[dict[str, str]]
    n_categories: int
    time_s: float


class DefaultWarehouseResponse(BaseModel):
    n_aisles: int
    n_positions_per_aisle: int
    aisle_width: float
    position_spacing: float
    depot: list[int]
    total_positions: int
    description: str


class OrderItem(BaseModel):
    order_id: str
    categories: list[str] = Field(min_length=1)


class InferRequest(BaseModel):
    orders: list[OrderItem] = Field(min_length=1)
    seed: Optional[int] = Field(default=None)


class InferResponse(BaseModel):
    batches: list[dict[str, Any]]
    distance_comparison: dict[str, Any]
    slotting_map: dict[str, dict[str, int]]
    summary: dict[str, Any]
    details: Optional[dict[str, Any]] = None


class MLErrorResponse(BaseModel):

    error: str
    message: str
    details: Optional[dict[str, Any]] = None