import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.ml_state import MLState
from app.schemas.ml import DefaultWarehouseResponse, TrainResponse
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ML"])
_service = MLService()

def _get_state(request: Request) -> MLState:
    return request.app.state.ml_state

@router.post("/train", response_model=TrainResponse)
async def train(request: Request):
    """Re-trigger training."""
    state = _get_state(request)
    try:
        meta = _service.train(state)
        return {"status": "ok", **meta}
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "TRAINING_FAILED", "message": str(e)},
        )

@router.get("/warehouse/default", response_model=DefaultWarehouseResponse)
async def get_default_warehouse(request: Request):
    """Ambil default warehouse config."""
    state = _get_state(request)
    if not state.is_trained:
        raise HTTPException(
            status_code=422,
            detail={"error": "NOT_TRAINED", "message": "Model belum di-train."},
        )
    from ml.service import get_default_warehouse_config

    default = get_default_warehouse_config()
    return {
        "n_aisles": default.n_aisles,
        "n_positions_per_aisle": default.n_positions_per_aisle,
        "aisle_width": default.aisle_width,
        "position_spacing": default.position_spacing,
        "depot": list(default.depot),
        "total_positions": default.total_positions,
        "description": f"Default config: {default.total_positions} slot, {default.n_aisles} lorong.",
    }