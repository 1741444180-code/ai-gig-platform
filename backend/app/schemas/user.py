"""Pydantic schemas for User endpoints."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    phone: str
    nickname: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    phone: str
    nickname: Optional[str]
    avatar_url: Optional[str]
    role: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
