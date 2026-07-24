from pydantic import BaseModel
from typing import List

class DatasetItem(BaseModel):
    id: str
    name: str

class DatasetsResponse(BaseModel):
    datasets: List[DatasetItem]
