"""User model — platform users (需求方 / Agent运营方)."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="user")  # user | agent | admin
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | banned
    # JWT auth fields (auth-01)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=True)
    sms_code: Mapped[str] = mapped_column(String(10), nullable=True)
    sms_code_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
