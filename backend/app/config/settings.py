import random
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Warehouse Recommendation API"
    PROJECT_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    ENV: str = "development"

    DATA_CSV_PATH: str = "app/data/indonesia_e-commerce_sales_and_shipping_2023–2025/all_months_clean.csv"
    ML_RANDOM_SEED: Optional[int] = None

    def get_random_seed(self) -> int:
        if self.ML_RANDOM_SEED is not None:
            return self.ML_RANDOM_SEED
        return random.randint(10, 9999)

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
