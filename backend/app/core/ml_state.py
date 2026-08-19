from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MLState:
    # random seed
    seed: Optional[int] = None

    # hasil training
    is_trained: bool = False
    affinity: Optional[Any] = None
    categories: list[str] = field(default_factory=list)
    frequencies: dict[str, int] = field(default_factory=dict)
    train_data: Optional[Any] = None
    train_meta: dict[str, Any] = field(default_factory=dict)

    cached_orders: Optional[list[dict]] = None

    is_configured: bool = False
    warehouse_result: Optional[Any] = None

    is_training: bool = False
    training_error: Optional[str] = None

    def reset_warehouse(self) -> None:
        self.is_configured = False
        self.warehouse_result = None
