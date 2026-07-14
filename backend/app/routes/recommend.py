from fastapi import APIRouter, Depends
from app.schemas.recommend import RecommendRequest, RecommendResponse
from app.services import RecommendService, get_recommend_service

router = APIRouter(tags=["Recommendation"])

@router.post("/recommend", response_model=RecommendResponse)
async def create_recommendation(
    payload: RecommendRequest,
    service: RecommendService = Depends(get_recommend_service)
):
    return service.generate_recommendation(payload.dataset)
