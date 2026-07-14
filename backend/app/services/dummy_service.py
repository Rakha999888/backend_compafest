import json
import os
from typing import List, Dict, Any
from fastapi import HTTPException
from app.utils.exceptions import DatasetNotFoundError

class DummyService:
    def __init__(self):
        # Resolve data path dynamically relative to service file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(current_dir, "..", "data")

    def get_dataset_data(self, dataset_id: str) -> List[Dict[str, Any]]:
        valid_datasets = {
            "small": "demo_small.json",
            "medium": "demo_medium.json",
            "large": "demo_large.json"
        }

        if dataset_id not in valid_datasets:
            raise DatasetNotFoundError(dataset_id)

        file_name = valid_datasets[dataset_id]
        file_path = os.path.join(self.data_dir, file_name)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            raise DatasetNotFoundError(dataset_id)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Failed to parse database file {file_name}.")

dummy_service = DummyService()
