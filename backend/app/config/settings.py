from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Warehouse Recommendation API"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    # DATA_CSV_PATH bisa di-override via env var di docker-compose.yml
    DATA_CSV_PATH: str = "data/indonesia_e-commerce_sales_and_shipping_2023\u20132025/all_months_clean.csv"
    ML_TRAIN_MONTHS: int = 21
    ML_TEST_MONTHS: int = 3
    ML_RANDOM_SEED: int = 42

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
