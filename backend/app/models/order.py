"""Order model — matched demand + agent + price."""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    demand_id: Mapped[str] = mapped_column(String(36), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0)  # 平台抽成 (自有Agent=0)
    deposit: Mapped[float] = mapped_column(Float, default=0.0)  # 保证金
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending | accepted | in_progress | submitted | completed | cancelled | disputed
    delivery_url: Mapped[str] = mapped_column(String(512), nullable=True)
    delivery_note: Mapped[str] = mapped_column(Text, nullable=True)
    accept_note: Mapped[str] = mapped_column(Text, nullable=True)  # 验收备注
    cancel_reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
