from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class MLState:
    # hasil training
    is_trained: bool = False
    affinity: Optional[Any] = None
    categories: list[str] = field(default_factory=list)
    frequencies: dict[str, int] = field(default_factory=dict)
    train_data: Optional[Any] = None
    train_meta: dict[str, Any] = field(default_factory=dict)

    # hasil konfigurasi gudang
    is_configured: bool = False
    warehouse_result: Optional[Any] = None

    def reset_warehouse(self) -> None:
        """Reset config gudang tanpa re-training."""
        self.is_configured = False
        self.warehouse_result = None
