"""Pydantic schemas for Agent endpoints."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    api_url: str
    api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    mode: str = "auto"  # auto | manual


class AgentResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    api_url: str
    webhook_url: Optional[str]
    capabilities: Optional[str]
    mode: str
    is_verified: bool
    credit_score: int
    completed_count: int
    failed_count: int
    free_trial_remaining: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
