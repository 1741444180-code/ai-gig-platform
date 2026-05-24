"""Pydantic schemas for Demand endpoints."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DemandCreate(BaseModel):
    title: str
    description: str
    budget: Optional[float] = None
    attachments: Optional[List[str]] = None
    deadline: Optional[datetime] = None


class DemandResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    category: Optional[str]
    tags: Optional[str]
    budget: Optional[float]
    publisher_type: str
    fulfill_mode: str
    match_status: str
    status: str
    ai_structured: Optional[str]
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}