from fastapi import APIRouter, HTTPException
from app.schemas.recommend import RecommendRequest, RecommendResponse
from app.services.recommendation_service import RecommendationService
from app.repositories.order_repository import get_order_repository
from app.adapters.ml_adapter import get_ml_adapter
from app.services.dummy_service import dummy_service
from typing import List

router = APIRouter(prefix="/recommend", tags=["recommend"])


def get_recommendation_service() -> RecommendationService:
    return RecommendationService(
        order_repo=get_order_repository(),
        ml_adapter=get_ml_adapter()
    )


@router.post("", response_model=RecommendResponse)
async def create_recommendation(request: RecommendRequest):
    try:
        if request.dataset:
            transactions = dummy_service.get_dataset_data(request.dataset)
            order_ids = list(set(tx["order_id"] for tx in transactions))
        elif request.order_ids:
            order_ids = request.order_ids
        else:
            raise HTTPException(
                status_code=422,
                detail="Either 'dataset' or 'order_ids' must be provided"
            )
        
        service = get_recommendation_service()
        result = service.recommend(order_ids)
        
        if "error" in result:
            return RecommendResponse(
                success=False,
                message="No orders found",
                error=result["error"]
            )
        
        return RecommendResponse(
            success=True,
            message="Recommendation generated successfully",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
