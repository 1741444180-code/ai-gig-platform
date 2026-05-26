"""Agent model — AI Agent registry with API endpoint + capability profile."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    api_url: Mapped[str] = mapped_column(String(512), nullable=True)  # Agent callback URL（可选，Agent自有服务）
    webhook_url: Mapped[str] = mapped_column(String(512), nullable=True)  # 平台推送需求的webhook地址
    capabilities: Mapped[str] = mapped_column(Text, nullable=True)  # JSON: ["文案", "图片生成", ...]
    mode: Mapped[str] = mapped_column(String(16), default="auto")  # auto | manual
    # agent-01: API Key + 运营字段
    api_key_hash: Mapped[str] = mapped_column(String(256), nullable=True)  # SHA-256 hash of api_key
    webhook_secret: Mapped[str] = mapped_column(String(128), nullable=True)  # Webhook签名密钥
    api_key_count: Mapped[int] = mapped_column(Integer, default=0)  # 当前有效API Key数量
    rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # API调用速率限制（次/分钟）
    # agent-01: 自有Agent + 接单参数
    is_owner_agent: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否平台自有Agent
    auto_accept_timeout: Mapped[int] = mapped_column(Integer, default=30)  # 自动接单超时（分钟，自有Agent）
    max_concurrent: Mapped[int] = mapped_column(Integer, default=5)  # 最大并发接单数
    base_price: Mapped[int] = mapped_column(Integer, default=0)  # 基础报价（分）
    daily_limit: Mapped[int] = mapped_column(Integer, default=50)  # 每日接单上限
    eta_hours: Mapped[int] = mapped_column(Integer, default=24)  # 预计交付时间（小时）
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    credit_score: Mapped[int] = mapped_column(Integer, default=100)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    free_trial_remaining: Mapped[int] = mapped_column(Integer, default=3)  # 前3单免保证金
    # wallet-01: 收益钱包字段
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 可用余额
    frozen_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 冻结余额（提现中）
    total_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 累计收入
    # vector-03: 语义匹配向量字段 (1536维, 通义千问 text-embedding-v2)
    description_vec: Mapped[list] = mapped_column(Vector(1536), nullable=True)
    capabilities_vec: Mapped[list] = mapped_column(Vector(1536), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
