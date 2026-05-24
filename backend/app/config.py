"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ═══════════════════════════════════════════════════════════
    # Database
    # ═══════════════════════════════════════════════════════════
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_gig"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/ai_gig"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ═══════════════════════════════════════════════════════════
    # JWT
    # ═══════════════════════════════════════════════════════════
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # ═══════════════════════════════════════════════════════════
    # WeChat
    # ═══════════════════════════════════════════════════════════
    wechat_app_id: str = ""
    wechat_app_secret: str = ""

    # ═══════════════════════════════════════════════════════════
    # AI / DashScope (通义千问)
    # ═══════════════════════════════════════════════════════════
    dashscope_api_key: str = ""
    qwen_api_key: str = ""                       # alias used by ai_service.py
    ai_model: str = "qwen-plus"
    qwen_model: str = "qwen-plus"               # alias used by ai_service.py

    # ═══════════════════════════════════════════════════════════
    # 平台业务配置
    # ═══════════════════════════════════════════════════════════
    platform_fee_rate: float = 0.10              # 标准平台费率 10%
    max_modify_times: int = 3                    # 订单最大修改次数

    # ═══════════════════════════════════════════════════════════
    # CORS
    # ═══════════════════════════════════════════════════════════
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ═══════════════════════════════════════════════════════════
    # App
    # ═══════════════════════════════════════════════════════════
    app_env: str = "development"
    debug: bool = True

    # ─── Legacy / alias properties (for backward compat) ───

    @property
    def SECRET_KEY(self) -> str:
        """Alias for secret_key used by security.py"""
        return self.secret_key

    @property
    def ALGORITHM(self) -> str:
        """Alias for algorithm used by security.py"""
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

    @property
    def QWEN_API_KEY(self) -> str:
        """Resolve QWEN_API_KEY: qwen_api_key > dashscope_api_key > ''"""
        return self.qwen_api_key or self.dashscope_api_key

    @property
    def QWEN_MODEL(self) -> str:
        """Resolve QWEN_MODEL: qwen_model > ai_model > 'qwen-plus'"""
        return self.qwen_model or self.ai_model or "qwen-plus"

    @property
    def PLATFORM_FEE_RATE(self) -> float:
        return self.platform_fee_rate

    @property
    def MAX_MODIFY_TIMES(self) -> int:
        return self.max_modify_times

    model_config = {"env_prefix": "APP_", "env_file": ".env", "extra": "ignore"}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
