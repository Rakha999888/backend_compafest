from pydantic import BaseModel
from typing import List

class RecommendSummary(BaseModel):
    warehouse: str
    total_orders: int
    total_items: int

class SlottingItem(BaseModel):
    product: str
    location: str

class SlottingOptimization(BaseModel):
    before: List[SlottingItem]
    after: List[SlottingItem]

class DistanceMetrics(BaseModel):
    before: float
    after: float
    saved: float
    saving_percentage: float

class RecommendationData(BaseModel):
    summary: RecommendSummary
    slotting: SlottingOptimization
    picking_route: List[str]
    distance: DistanceMetrics

class RecommendRequest(BaseModel):
    dataset: str

class RecommendResponse(BaseModel):
    success: bool
    message: str
    data: RecommendationData
