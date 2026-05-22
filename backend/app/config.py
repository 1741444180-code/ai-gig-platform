"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_gig"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/ai_gig"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # WeChat
    wechat_app_id: str = ""
    wechat_app_secret: str = ""

    # AI
    dashscope_api_key: str = ""
    ai_model: str = "qwen-plus"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # App
    app_env: str = "development"
    debug: bool = True

    # ─── Legacy aliases for code that uses settings.SECRET_KEY etc. ───

    @property
    def SECRET_KEY(self) -> str:
        return self.secret_key

    @property
    def ALGORITHM(self) -> str:
        return self.algorithm

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.access_token_expire_minutes

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        return self.refresh_token_expire_days

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url

    @property
    def DB_POOL_SIZE(self) -> int:
        return self.db_pool_size

    @property
    def DB_MAX_OVERFLOW(self) -> int:
        return self.db_max_overflow

    model_config = {"env_prefix": "APP_", "env_file": ".env", "extra": "ignore"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
