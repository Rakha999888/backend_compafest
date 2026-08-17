from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from enum import Enum

class ReasonCode(str, Enum):
    HIGH_AFFINITY = "HIGH_AFFINITY"
    FREQUENCY_BASED = "FREQUENCY_BASED"
    DISTANCE_REDUCTION = "DISTANCE_REDUCTION"
    COMBINED = "COMBINED"


class CoPurchasedItem(BaseModel):
    product: str
    frequency: int
    confidence: float
    lift: float


class SlottingJustification(BaseModel):
    reason_code: ReasonCode
    confidence: Optional[float] = Field(None, ge=0, le=1)
    lift: Optional[float] = Field(None, ge=0)
    support: Optional[float] = Field(None, ge=0, le=1)
    co_purchased_with: List[CoPurchasedItem] = []
    human_readable_reason: str


class SlottingRecommendation(BaseModel):
    product: str
    from_location: str
    to_location: str
    justification: SlottingJustification


class ARMAnalysis(BaseModel):
    total_transactions: int
    total_products: int
    frequent_itemsets_found: int
    rules_generated: int
    min_support_used: float
    min_confidence_used: float
    top_rules: List[Dict] = []


class SlottingOptimizationV2(BaseModel):
    recommendations: List[SlottingRecommendation] = []
    total_items_moved: int
    arm_analysis: Optional[ARMAnalysis] = None


class AlgorithmParameters(BaseModel):
    population_size: int
    generations: int
    crossover_rate: float
    mutation_rate: float


class ConvergenceInfo(BaseModel):
    generations_run: int
    convergence_generation: Optional[int] = None
    initial_fitness: float
    final_fitness: float
    improvement_percentage: float


class BaselineComparison(BaseModel):
    vs_random: Dict[str, float] = {}
    vs_abc: Dict[str, float] = {}


class RouteJustification(BaseModel):
    algorithm_used: str
    algorithm_parameters: AlgorithmParameters
    convergence_info: ConvergenceInfo
    baseline_comparison: BaselineComparison
    human_readable_reason: str


class PickingRouteV2(BaseModel):
    optimized_route: List[str]
    original_route: Optional[List[str]] = None
    distance_before: float
    distance_after: float
    distance_saved: float
    saving_percentage: float
    justification: Optional[RouteJustification] = None


class DistanceMetricsV2(BaseModel):
    before: float
    after: float
    saved: float
    saving_percentage: float
    manhattan_distance_breakdown: List[Dict] = []


class RecommendSummaryV2(BaseModel):
    warehouse: str
    total_orders: int
    total_items: int
    unique_products: int
    processing_time_ms: int


class RecommendationDataV2(BaseModel):
    summary: RecommendSummaryV2
    slotting: SlottingOptimizationV2
    picking_route: PickingRouteV2
    distance: DistanceMetricsV2
    metadata: Dict = {}


class RecommendResponseV2(BaseModel):
    success: bool
    message: str
    data: RecommendationDataV2
    explainability_version: str = "1.0"