"""订单相关Schema定义"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class OrderResponse(BaseModel):
    """订单详情响应"""
    id: uuid.UUID
    requirement_id: uuid.UUID
    user_id: uuid.UUID
    agent_id: uuid.UUID
    amount: float
    platform_fee: float
    agent_income: float
    status: str
    payment_method: Optional[str] = None
    payment_id: Optional[str] = None
    deliverables: list[str]
    delivery_message: Optional[str] = None
    ai_review_score: Optional[float] = None
    user_confirm: Optional[int] = None
    modify_count: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """订单列表响应"""
    total: int
    items: list[OrderResponse]


class OrderStatusResponse(BaseModel):
    """订单状态响应"""
    id: uuid.UUID
    status: str
    modify_count: int
    ai_review_score: Optional[float] = None
    user_confirm: Optional[int] = None
    completed_at: Optional[datetime] = None


class ConfirmOrderRequest(BaseModel):
    """确认验收请求"""
    comment: Optional[str] = Field(None, description="验收评价", max_length=500)


class RejectOrderRequest(BaseModel):
    """拒绝验收请求"""
    reason: str = Field(..., description="拒绝原因", max_length=500)
