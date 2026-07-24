from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.services.recommend_service import RecommendService, get_recommend_service

router = APIRouter(tags=["Recommendation"])


class InferenceOrder(BaseModel):
    order_id: str
    categories: List[str] = Field(min_items=1)


class RecommendRequest(BaseModel):
    orders: List[InferenceOrder] = Field(min_items=1)
    seed: Optional[int] = 42


class FullPipelineRequest(BaseModel):
    data_source: str
    max_orders: Optional[int] = None
    seed: Optional[int] = 42


@router.post("/recommend")
async def recommend(
    payload: RecommendRequest,
    service: RecommendService = Depends(get_recommend_service),
):
    orders = [
        {"order_id": o.order_id, "categories": o.categories}
        for o in payload.orders
    ]
    return await service.recommend(orders=orders, seed=payload.seed or 42)


@router.post("/recommend/full-pipeline")
async def full_pipeline(
    payload: FullPipelineRequest,
    service: RecommendService = Depends(get_recommend_service),
):
    return await service.full_pipeline(
        data_source=payload.data_source,
        max_orders=payload.max_orders,
        seed=payload.seed or 42,
    )