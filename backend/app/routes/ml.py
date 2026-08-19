import logging

from fastapi import APIRouter, HTTPException, Request

from app.core.ml_state import MLState
from app.schemas.ml import (
    DefaultWarehouseResponse,
    InferRequest,
    InferResponse,
    TrainResponse,
    WarehouseConfigRequest,
    WarehouseConfigResponse,
)
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

@router.post("/warehouse", response_model=WarehouseConfigResponse)
async def configure_warehouse(
    request: Request,
    payload: WarehouseConfigRequest = WarehouseConfigRequest(),
):
    """Setup warehouse grid + slotting."""
    state = _get_state(request)
    if not state.is_trained:
        raise HTTPException(
            status_code=422,
            detail={"error": "NOT_TRAINED", "message": "Jalankan POST /api/ml/train dulu."},
        )
    try:
        config_dict = payload.model_dump(exclude_none=True)
        return _service.configure_warehouse(state, config_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "GRID_TOO_SMALL", "message": str(e)},
        )

@router.post("/infer", response_model=InferResponse)
async def infer(request: Request, payload: InferRequest):
    """Inference per request (kirim orders -> dapat batches + routes)."""
    state = _get_state(request)
    if not state.is_trained:
        raise HTTPException(
            status_code=422,
            detail={"error": "NOT_TRAINED", "message": "Model belum di-train."},
        )
    if not state.is_configured:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "WAREHOUSE_NOT_CONFIGURED",
                "message": "Jalankan POST /api/ml/warehouse dulu.",
            },
        )
    try:
        orders = [o.model_dump() for o in payload.orders]
        return _service.infer(state, orders, payload.seed)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "EMPTY_ORDERS", "message": str(e)},
        )

@router.get("/status")
async def ml_status(request: Request):
    """Cek status training ML model."""
    state = _get_state(request)
    return {
        "is_training": state.is_training,
        "is_trained": state.is_trained,
        "is_configured": state.is_configured,
        "training_error": state.training_error,
        "n_categories": len(state.categories),
        "n_cached_orders": len(state.cached_orders) if state.cached_orders else 0,
        "train_meta": state.train_meta,
    }