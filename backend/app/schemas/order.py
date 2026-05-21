"""Pydantic schemas for Order endpoints."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class QuoteCreate(BaseModel):
    """Agent报价请求"""
    price: float
    accept_note: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    demand_id: str
    agent_id: str
    user_id: str
    price: float
    platform_fee: float
    deposit: float
    status: str
    delivery_url: Optional[str]
    delivery_note: Optional[str]
    accept_note: Optional[str]
    cancel_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
