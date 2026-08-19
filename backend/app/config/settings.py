import random
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Warehouse Recommendation API"
    PROJECT_VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    CORS_ORIGINS: str = "*"
    RATE_LIMIT_PER_MINUTE: int = 60

    ML_SERVICE_URL: str = "http://localhost:8001"
    ML_SERVICE_TIMEOUT: int = 300
    USE_MOCK_ML: bool = False

    MAX_UPLOAD_SIZE: int = 10_485_760
    PROCESSING_TIMEOUT: int = 30_000

    LOG_LEVEL: str = "INFO"

    DATA_CSV_PATH: str = "app/data/indonesia-e-commerce-sales-and-shipping-2023-2025/all_months_clean.csv"
    ML_RANDOM_SEED: Optional[int] = None

    def get_random_seed(self) -> int:
        if self.ML_RANDOM_SEED is not None:
            return self.ML_RANDOM_SEED
        return random.randint(10, 9999)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()