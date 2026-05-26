"""Demand model — user's need/request posted on the platform."""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, func
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Demand(Base):
    __tablename__ = "demands"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=True)  # AI自动分类
    tags: Mapped[str] = mapped_column(String(256), nullable=True)  # JSON array
    budget: Mapped[float] = mapped_column(Float, nullable=True)
    attachments: Mapped[str] = mapped_column(Text, nullable=True)  # JSON: image/file URLs
    # demand-01: 扩展字段
    publisher_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # user | agent
    fulfill_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")  # auto | manual
    match_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending | matched | timeout
    status: Mapped[str] = mapped_column(
        String(16), default="open"
    )  # open | quoted | matched | in_progress | completed | cancelled
    ai_structured: Mapped[str] = mapped_column(Text, nullable=True)  # AI结构化后的JSON
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    # vector-04: 需求向量化字段
    demand_vec: Mapped[list] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
