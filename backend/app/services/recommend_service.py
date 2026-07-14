from typing import Dict, Any
from app.services.recommend_pipeline import BaseRecommendationPipeline, DummyRecommendationPipeline

class RecommendService:
    def __init__(self, pipeline: BaseRecommendationPipeline):
        self.pipeline = pipeline

    def generate_recommendation(self, dataset_id: str) -> Dict[str, Any]:
        # Execute the pipeline (delegated to injected pipeline, currently dummy, later ML)
        recommendation_data = self.pipeline.run_pipeline(dataset_id)
        
        return {
            "success": True,
            "message": "Recommendation generated successfully",
            "data": recommendation_data
        }

# Dependency injection helper provider
def get_recommend_service() -> RecommendService:
    # We can inject any subclass of BaseRecommendationPipeline here (e.g. MLRecommendationPipeline in the future)
    pipeline = DummyRecommendationPipeline()
    return RecommendService(pipeline=pipeline)
