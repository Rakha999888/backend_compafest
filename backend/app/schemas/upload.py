from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None
    rows: Optional[int] = None
    unique_products: Optional[int] = None
