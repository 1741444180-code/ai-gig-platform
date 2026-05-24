"""Pydantic schemas for Agent endpoints (updated for agent-01~04)."""

from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import json


class AgentRegisterRequest(BaseModel):
    """Agent 注册请求 (agent-04): 3步合并为1步。"""
    name: str
    description: str
    capabilities: List[str]
    mode: str = "auto"  # auto | manual
    webhook_url: Optional[str] = None
    api_url: Optional[str] = None  # Agent 自有服务URL（可选）

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v):
        if not v or len(v) == 0:
            raise ValueError("capabilities 不能为空")
        if len(v) > 20:
            raise ValueError("capabilities 最多20个标签")
        return v

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v not in ("auto", "manual"):
            raise ValueError("mode 必须是 auto 或 manual")
        return v


class AgentRegisterResponse(BaseModel):
    """Agent 注册响应：包含明文 API Key（仅此一次可见）。"""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    api_url: Optional[str]
    webhook_url: Optional[str]
    capabilities: Optional[str]
    mode: str
    # 敏感信息：仅注册时返回
    api_key: str  # 明文API Key，仅此一次
    webhook_secret: str  # Webhook签名密钥
    is_verified: bool
    credit_score: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentProfileUpdateRequest(BaseModel):
    """Agent 能力卡更新 (agent-05)。"""
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    mode: Optional[str] = None
    webhook_url: Optional[str] = None
    api_url: Optional[str] = None
    base_price: Optional[int] = None
    eta_hours: Optional[int] = None
    max_concurrent: Optional[int] = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v):
        if v is not None and v not in ("auto", "manual"):
            raise ValueError("mode 必须是 auto 或 manual")
        return v


class AgentResponse(BaseModel):
    """Agent 公开信息（不包含 API Key 等敏感数据）。"""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    api_url: Optional[str]
    webhook_url: Optional[str]
    capabilities: Optional[str]
    mode: str
    is_verified: bool
    is_owner_agent: bool
    credit_score: int
    base_price: int
    eta_hours: int
    max_concurrent: int
    completed_count: int
    failed_count: int
    free_trial_remaining: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyInfo(BaseModel):
    """API Key 信息（脱敏）。"""
    id: str  # key 的 hash 前8位作为标识
    prefix: str  # ak_
    masked: str  # ak_****...****abcd
    created_at: Optional[datetime] = None
    is_active: bool = True


class AgentKeysResponse(BaseModel):
    """Agent 所有 API Key 列表。"""
    agent_id: str
    keys: List[ApiKeyInfo]
    max_keys: int = 3
