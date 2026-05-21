"""需求相关Schema定义"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


# ==================== 需求发布 ====================

class RequirementCreate(BaseModel):
    """创建需求请求"""
    title: str = Field(..., description="需求标题", max_length=256)
    description: str = Field(..., description="需求描述")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")
    budget: Optional[float] = Field(None, description="预算金额（元）")
    urgency: int = Field(default=1, description="紧急度 1=普通 2=加急 3=特急")
    match_mode: str = Field(default="auto", description="匹配模式 auto=自动 manual=手动")

    model_config = {"from_attributes": True}


# ==================== 需求响应 ====================

class RequirementResponse(BaseModel):
    """需求详情响应"""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str
    category: Optional[str] = None
    tags: Optional[list] = None
    attachments: Optional[list] = None
    budget: Optional[float] = None
    urgency: int
    structured_data: Optional[dict] = None
    status: str
    match_mode: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RequirementListResponse(BaseModel):
    """需求列表分页响应"""
    requirements: List[RequirementResponse]
    total: int
    page: int
    page_size: int


# ==================== 需求修改 ====================

class RequirementUpdate(BaseModel):
    """修改需求请求"""
    title: Optional[str] = Field(None, description="需求标题", max_length=256)
    description: Optional[str] = Field(None, description="需求描述")
    attachments: Optional[List[str]] = Field(None, description="附件URL列表")
    budget: Optional[float] = Field(None, description="预算金额（元）")
    urgency: Optional[int] = Field(None, description="紧急度 1=普通 2=加急 3=特急")
    match_mode: Optional[str] = Field(None, description="匹配模式 auto=自动 manual=手动")


# ==================== 报价 ====================

class QuoteCreate(BaseModel):
    """提交报价请求"""
    price: float = Field(..., description="报价金额（元）", gt=0)
    delivery_hours: Optional[float] = Field(None, description="预计交付时间（小时）", gt=0)
    message: Optional[str] = Field(None, description="报价说明")


class QuoteResponse(BaseModel):
    """报价响应"""
    id: uuid.UUID
    requirement_id: uuid.UUID
    agent_id: uuid.UUID
    price: float
    delivery_hours: Optional[float] = None
    message: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== 匹配 ====================

class MatchResponse(BaseModel):
    """单个匹配结果"""
    agent_id: str
    agent_name: str
    agent_nickname: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None
    base_price: Optional[float] = None
    credit_score: int
    similarity: float
