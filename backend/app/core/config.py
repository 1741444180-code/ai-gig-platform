from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://aigig:aigig_dev_2026@localhost:5432/aigig"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7天

    # 通义千问
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen3.6-plus"
    DASHSCOPE_BASE_URL: str = "https://coding.dashscope.aliyuncs.com/v1"

    # 微信
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""

    # 阿里云OSS
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET: str = "aigig"
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"

    # 环境
    app_env: str = "development"

    # 业务配置
    PLATFORM_FEE_RATE: float = 0.10  # 10%平台抽成
    FREE_ORDERS_COUNT: int = 3  # 前3单免保证金
    MAX_MODIFY_TIMES: int = 1  # 最大修改次数

    model_config = {"env_prefix": "APP_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
