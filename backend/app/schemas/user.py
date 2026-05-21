"""用户相关Schema定义"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


# ==================== 认证相关 ====================

class WechatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="微信登录code")


class PhoneLoginRequest(BaseModel):
    """手机号登录请求"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")
    verify_code: str = Field(..., description="验证码", min_length=4, max_length=8)


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")


# ==================== Token相关 ====================

class Token(BaseModel):
    """认证Token响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class TokenData(BaseModel):
    """Token解析后的数据"""
    user_id: Optional[str] = None
    openid: Optional[str] = None


# ==================== 用户相关 ====================

class UserCreate(BaseModel):
    """创建用户请求（内部使用）"""
    openid: Optional[str] = None
    unionid: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    """用户信息响应"""
    id: uuid.UUID
    openid: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    status: int
    balance: float
    credit_score: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, description="昵称", max_length=64)
    avatar: Optional[str] = Field(None, description="头像URL", max_length=512)


class LoginResponse(BaseModel):
    """登录响应（包含token和用户信息）"""
    access_token: str
    token_type: str = "bearer"
    user_info: UserResponse
