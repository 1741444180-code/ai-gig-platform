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
    """手机验证码登录请求"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")
    verify_code: str = Field(..., description="验证码", min_length=4, max_length=8)


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")


class RegisterRequest(BaseModel):
    """用户注册请求（手机号+密码）"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")
    password: str = Field(..., description="密码", min_length=6, max_length=128)
    nickname: Optional[str] = Field(None, description="昵称", max_length=64)


class PasswordLoginRequest(BaseModel):
    """密码登录请求（手机号+密码）"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")
    password: str = Field(..., description="密码")


class RefreshTokenRequest(BaseModel):
    """Token刷新请求"""
    refresh_token: str = Field(..., description="refresh_token")


# ==================== Token相关 ====================

class Token(BaseModel):
    """认证Token响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class TokenData(BaseModel):
    """Token解析后的数据"""
    user_id: Optional[str] = None
    openid: Optional[str] = None


class TokenPair(BaseModel):
    """Access + Refresh Token 对"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="access_token过期时间(秒)")


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
    id: str
    openid: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, description="昵称", max_length=64)
    avatar: Optional[str] = Field(None, description="头像URL", max_length=512)


class LoginResponse(BaseModel):
    """登录响应（包含token和用户信息）"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_info: UserResponse
