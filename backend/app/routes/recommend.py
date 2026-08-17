from fastapi import APIRouter, HTTPException
from app.schemas.recommend import RecommendRequest, RecommendResponse
from app.services.recommend_service import get_recommend_service
from app.services.dummy_service import dummy_service
from app.repositories.order_repository import get_order_repository

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.post("")
async def create_recommendation(request: RecommendRequest):
    try:
        service = get_recommend_service()
        order_repo = get_order_repository()

        if request.dataset:
            # Use full pipeline mode untuk saat ini
            result = await service.full_pipeline(data_source=request.dataset)
            return result

        elif request.order_ids:
            order_data = order_repo.get_orders_with_categories(request.order_ids)
            orders = [
                {"order_id": o["order_id"], "categories": o["categories"]}
                for o in order_data
            ]
            result = await service.recommend(orders)
            return result

        else:
            raise HTTPException(
                status_code=422,
                detail="Either 'dataset' or 'order_ids' must be provided"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
