from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Warehouse Recommendation API"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
