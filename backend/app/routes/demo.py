from fastapi import APIRouter
from typing import List
from app.schemas.demo import DatasetsResponse
from app.schemas.transaction import Transaction
from app.services import demo_service, dummy_service

router = APIRouter(prefix="/demo", tags=["Demo"])

@router.get("/list", response_model=DatasetsResponse)
async def list_demo_datasets():
    datasets = demo_service.get_datasets()
    return {"datasets": datasets}

@router.get("/{dataset_id}", response_model=List[Transaction])
async def get_demo_dataset(dataset_id: str):
    return dummy_service.get_dataset_data(dataset_id)
