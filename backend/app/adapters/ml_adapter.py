
from typing import Dict, List
from app.ml.inference import run_inference


class MLAdapter:
    
    def __init__(self, min_support: float = 0.3, min_confidence: float = 0.7):
        self.min_support = min_support
        self.min_confidence = min_confidence
    
    def run(self, orders: List[Dict]) -> Dict:
        
        return run_inference(
            orders=orders,
            min_support=self.min_support,
            min_confidence=self.min_confidence
        )


def get_ml_adapter() -> MLAdapter:
    return MLAdapter()