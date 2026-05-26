"""Review model — post-order evaluation."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)  # 评价人（用户）
    reviewee_id: Mapped[str] = mapped_column(String(36), nullable=False)  # 被评价人（Agent）
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    content: Mapped[str] = mapped_column(Text, nullable=True)
    # review-03: 申诉相关字段
    is_appealed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # 是否被申诉
    appeal_reason: Mapped[str] = mapped_column(Text, nullable=True)  # 申诉理由
    appeal_status: Mapped[str] = mapped_column(String(20), nullable=True)  # none | pending | resolved
    admin_action: Mapped[str] = mapped_column(String(20), nullable=True)  # dismiss | delete
    admin_note: Mapped[str] = mapped_column(Text, nullable=True)  # 管理员备注
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
