"""Payment model — transaction records."""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=True)  # wechat | alipay
    transaction_id: Mapped[str] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | paid | refunded | released
    type: Mapped[str] = mapped_column(String(20))  # payment | refund | release
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
