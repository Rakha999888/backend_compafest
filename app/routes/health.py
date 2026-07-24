from fastapi import APIRouter
from app.schemas.health import HealthCheck

router = APIRouter()

@router.get("/health", response_model=HealthCheck, tags=["Health"])
async def check_health():
    return {
        "status": "ok",
        "service": "Warehouse Recommendation API",
        "version": "1.0.0"
    }
