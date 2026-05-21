"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_gig"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/ai_gig"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 720

    # AI
    dashscope_api_key: str = ""
    ai_model: str = "qwen-plus"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # App
    app_env: str = "development"
    debug: bool = True

    model_config = {"env_prefix": "APP_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
