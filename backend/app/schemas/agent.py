"""Agent能力卡相关Schema定义"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
import uuid


class AgentProfileCreate(BaseModel):
    """注册Agent能力卡请求"""
    name: str = Field(..., description="Agent名称", max_length=128)
    description: Optional[str] = Field(None, description="能力描述")
    tags: list[str] = Field(default=[], description="能力标签")
    capabilities: dict[str, Any] = Field(default={}, description="能力详情JSON")
    base_price: Optional[float] = Field(None, description="基础报价", gt=0)
    webhook_url: Optional[str] = Field(None, description="回调地址", max_length=512)
    auto_accept: bool = Field(default=False, description="自动接单开关")
    daily_limit: int = Field(default=0, description="每日接单上限，0=不限", ge=0)


class AgentProfileUpdate(BaseModel):
    """更新Agent能力卡请求"""
    name: Optional[str] = Field(None, description="Agent名称", max_length=128)
    description: Optional[str] = Field(None, description="能力描述")
    tags: Optional[list[str]] = Field(None, description="能力标签")
    capabilities: Optional[dict[str, Any]] = Field(None, description="能力详情JSON")
    base_price: Optional[float] = Field(None, description="基础报价", gt=0)
    webhook_url: Optional[str] = Field(None, description="回调地址", max_length=512)
    auto_accept: Optional[bool] = Field(None, description="自动接单开关")
    daily_limit: Optional[int] = Field(None, description="每日接单上限，0=不限", ge=0)


class AgentProfileResponse(BaseModel):
    """Agent能力卡响应"""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    tags: list[str]
    capabilities: dict[str, Any]
    base_price: Optional[float] = None
    api_key: str
    webhook_url: Optional[str] = None
    auto_accept: bool
    daily_limit: int
    today_orders: int
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentRegisterRequest(BaseModel):
    """注册Agent请求（包含用户信息）"""
    agent: AgentProfileCreate


class AgentOrderItem(BaseModel):
    """工作台订单条目"""
    order_id: uuid.UUID
    requirement_title: str
    amount: float
    status: str
    created_at: datetime
    deliverables: list[str]
    delivery_message: Optional[str] = None

    model_config = {"from_attributes": True}


class AgentOrderListResponse(BaseModel):
    """Agent接单工作台响应"""
    total: int
    items: list[AgentOrderItem]


class AcceptOrderRequest(BaseModel):
    """外部Agent接单请求"""
    api_key: str = Field(..., description="Agent API Key")
    requirement_id: uuid.UUID = Field(..., description="需求ID")


class SubmitDeliveryRequest(BaseModel):
    """外部Agent提交交付物请求"""
    api_key: str = Field(..., description="Agent API Key")
    order_id: uuid.UUID = Field(..., description="订单ID")
    deliverables: list[str] = Field(..., description="交付物URL列表")
    delivery_message: Optional[str] = Field(None, description="交付说明")
