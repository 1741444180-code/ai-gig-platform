"""Review model — post-order evaluation."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewee_id: Mapped[str] = mapped_column(String(36), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    content: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
