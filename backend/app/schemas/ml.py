from typing import Any, Optional
from pydantic import BaseModel, Field

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

class MLErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict[str, Any]] = None