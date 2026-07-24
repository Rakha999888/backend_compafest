from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Warehouse Recommendation API"
    PROJECT_VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    CORS_ORIGINS: str = "*"
    RATE_LIMIT_PER_MINUTE: int = 60

    ML_SERVICE_URL: str = "http://localhost:8001"
    ML_SERVICE_TIMEOUT: int = 60
    USE_MOCK_ML: bool = True

    MAX_UPLOAD_SIZE: int = 10_485_760
    PROCESSING_TIMEOUT: int = 30_000

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()