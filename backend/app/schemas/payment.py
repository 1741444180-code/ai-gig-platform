"""支付相关Schema定义"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


# ==================== 创建支付 ====================

class PaymentCreateRequest(BaseModel):
    """发起支付请求"""
    order_id: uuid.UUID = Field(..., description="订单ID")
    payment_method: str = Field(..., description="支付方式", pattern="^(wechat|alipay|manual)$")


class PaymentCreateResponse(BaseModel):
    """支付创建响应"""
    payment_id: uuid.UUID
    order_id: uuid.UUID
    amount: float
    payment_method: str
    status: str
    pay_url: Optional[str] = Field(None, description="支付跳转URL（H5支付用）")
    created_at: datetime


# ==================== 支付回调 ====================

class PaymentCallbackRequest(BaseModel):
    """支付平台回调数据"""
    transaction_id: str = Field(..., description="支付平台交易号")
    order_id: uuid.UUID = Field(..., description="关联订单ID")
    status: str = Field(..., description="支付状态", pattern="^(success|failed)$")
    raw_data: Optional[dict] = Field(None, description="回调原始数据")


# ==================== 退款 ====================

class RefundRequest(BaseModel):
    """退款请求"""
    order_id: uuid.UUID = Field(..., description="订单ID")
    reason: str = Field(..., description="退款原因", max_length=500)


# ==================== 查询 ====================

class PaymentResponse(BaseModel):
    """支付记录详情"""
    id: uuid.UUID
    order_id: uuid.UUID
    user_id: uuid.UUID
    amount: float
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    status: str
    type: str
    raw_response: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    """支付记录列表"""
    payments: list[PaymentResponse]
    total: int
    page: int
    page_size: int
