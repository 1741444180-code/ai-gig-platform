"""Agent API Key 管理 Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ApiKeyCreateRequest(BaseModel):
    """创建 API Key 请求"""
    key_name: Optional[str] = Field(None, description="Key 名称/备注", max_length=64)
    scope: str = Field(default="full", description="权限范围: full=read_write sandbox=沙箱测试", pattern="^(full|read|sandbox|sandbox_test)$")
    is_sandbox: bool = Field(default=False, description="是否沙箱 Key（独立环境）")


class ApiKeyResponse(BaseModel):
    """API Key 响应"""
    id: uuid.UUID
    key_name: Optional[str] = None
    key_prefix: str  # 前 8 位，用于展示
    scope: str
    is_active: bool
    is_sandbox: bool
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyFullResponse(BaseModel):
    """API Key 创建时返回完整 Key（仅创建时显示一次）"""
    id: uuid.UUID
    full_key: str  # 完整 Key（仅创建时返回）
    key_name: Optional[str] = None
    key_prefix: str
    scope: str
    is_sandbox: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyListResponse(BaseModel):
    """API Key 列表"""
    keys: list[ApiKeyResponse]
    total: int
