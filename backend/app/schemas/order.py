"""Pydantic schemas for Order endpoints (order-01~07 updated)."""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class AgentQuoteRequest(BaseModel):
    """Agent接单请求 (order-02)"""
    price: float
    eta_hours: Optional[int] = None
    accept_note: Optional[str] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("价格必须大于0")
        return v


class AgentDeliverRequest(BaseModel):
    """Agent交付请求 (order-03)"""
    delivery_url: str
    delivery_note: Optional[str] = None


class AgentCancelRequest(BaseModel):
    """Agent取消接单请求 (order-05)"""
    cancel_reason: str


class OrderResponse(BaseModel):
    id: str
    demand_id: str
    agent_id: str
    user_id: str
    price: float
    platform_fee: float
    deposit: float
    status: str
    eta_hours: int
    delivery_url: Optional[str]
    delivery_note: Optional[str]
    accept_note: Optional[str]
    reject_reason: Optional[str]
    cancel_reason: Optional[str]
    reject_count: int
    delivery_attempts: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
