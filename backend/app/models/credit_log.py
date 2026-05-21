"""CreditLog model — Agent credit score change log."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class CreditLog(Base):
    __tablename__ = "credit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    order_id: Mapped[str] = mapped_column(String(36), nullable=True)
    change: Mapped[int] = mapped_column(Integer, nullable=False)  # +5, -10, etc.
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    before_score: Mapped[int] = mapped_column(Integer, nullable=False)
    after_score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
