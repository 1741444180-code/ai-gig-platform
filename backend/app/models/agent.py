"""Agent model — AI Agent registry with API endpoint + capability profile."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, DateTime, func
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
    api_url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str] = mapped_column(String(256), nullable=True)  # agent's own key if needed
    webhook_url: Mapped[str] = mapped_column(String(512), nullable=True)
    capabilities: Mapped[str] = mapped_column(Text, nullable=True)  # JSON: ["文案", "图片生成", ...]
    mode: Mapped[str] = mapped_column(String(16), default="auto")  # auto | manual
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    credit_score: Mapped[int] = mapped_column(Integer, default=100)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    free_trial_remaining: Mapped[int] = mapped_column(Integer, default=3)  # 前3单免保证金
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
