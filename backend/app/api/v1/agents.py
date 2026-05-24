"""Agent API endpoints — 注册/能力卡/Key管理 (agent-04/05/06/08)."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import (
    AgentRegisterRequest,
    AgentRegisterResponse,
    AgentProfileUpdateRequest,
    AgentResponse,
    ApiKeyInfo,
    AgentKeysResponse,
)
from app.core.security import get_current_user
from app.services.agent_key_service import (
    generate_api_key,
    hash_api_key,
    generate_webhook_secret,
    get_current_agent,
)

router = APIRouter()
MAX_API_KEYS = 3


# ── Agent 注册 (agent-04) ────────────────────────────────────────

@router.post("/register", response_model=AgentRegisterResponse, status_code=201)
async def register_agent(
    req: AgentRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Agent 3步注册合并 (agent-04).

    明文API Key仅在此时返回一次，请妥善保存。
    """
    plain_key, key_hash = generate_api_key()
    webhook_secret = generate_webhook_secret()

    agent = Agent(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        api_url=req.api_url,
        webhook_url=req.webhook_url,
        capabilities=json.dumps(req.capabilities, ensure_ascii=False),
        mode=req.mode,
        api_key_hash=key_hash,
        webhook_secret=webhook_secret,
        api_key_count=1,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentRegisterResponse(
        id=agent.id,
        user_id=agent.user_id,
        name=agent.name,
        description=agent.description,
        api_url=agent.api_url,
        webhook_url=agent.webhook_url,
        capabilities=agent.capabilities,
        mode=agent.mode,
        api_key=plain_key,
        webhook_secret=webhook_secret,
        is_verified=agent.is_verified,
        credit_score=agent.credit_score,
        status=agent.status,
        created_at=agent.created_at,
    )


# ── Agent 能力卡 (agent-05) ──────────────────────────────────────

@router.put("/profile", response_model=AgentResponse)
async def update_agent_profile(
    req: AgentProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent 能力卡更新 (agent-05)."""
    if req.name is not None:
        agent.name = req.name
    if req.description is not None:
        agent.description = req.description
    if req.capabilities is not None:
        agent.capabilities = json.dumps(req.capabilities, ensure_ascii=False)
    if req.mode is not None:
        agent.mode = req.mode
    if req.webhook_url is not None:
        agent.webhook_url = req.webhook_url
    if req.api_url is not None:
        agent.api_url = req.api_url
    if req.base_price is not None:
        agent.base_price = req.base_price
    if req.eta_hours is not None:
        agent.eta_hours = req.eta_hours
    if req.max_concurrent is not None:
        agent.max_concurrent = req.max_concurrent

    agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(agent)
    return agent


# ── API Key 管理 (agent-06) ──────────────────────────────────────

class RotateKeyResponse(BaseModel):
    """轮换API Key的响应 — 包含新明文Key."""
    id: str
    name: str
    api_key: str
    message: str = "API Key 已轮换，旧Key立即失效"


@router.post("/keys/rotate", response_model=RotateKeyResponse)
async def rotate_api_key(
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """轮换 API Key (agent-06)."""
    plain_key, key_hash = generate_api_key()
    agent.api_key_hash = key_hash
    agent.api_key_count = 1
    agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(agent)
    return RotateKeyResponse(
        id=agent.id,
        name=agent.name,
        api_key=plain_key,
    )


@router.post("/keys/revoke")
async def revoke_api_key(
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """撤销 API Key (agent-06)."""
    agent.api_key_hash = None
    agent.api_key_count = 0
    agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"success": True, "message": "API Key 已撤销"}


@router.get("/keys", response_model=AgentKeysResponse)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """查看当前 API Key 信息（脱敏）(agent-06)."""
    keys = []
    if agent.api_key_hash:
        masked = f"ak_{'*' * 8}...{agent.api_key_hash[-4:]}"
        keys.append(ApiKeyInfo(
            id=agent.api_key_hash[:8],
            prefix="ak_",
            masked=masked,
            created_at=agent.created_at,
            is_active=True,
        ))
    return AgentKeysResponse(
        agent_id=agent.id,
        keys=keys,
        max_keys=MAX_API_KEYS,
    )


# ── 自有Agent配置 (agent-08) ─────────────────────────────────────

class OwnerAgentConfigRequest(BaseModel):
    """配置自有Agent请求."""
    is_owner_agent: bool = True
    auto_accept_timeout: int = 30
    max_concurrent: int = 5
    base_price: int = 0
    daily_limit: int = 50
    eta_hours: int = 24


@router.put("/{agent_id}/owner-config", response_model=AgentResponse)
async def configure_owner_agent(
    agent_id: str,
    req: OwnerAgentConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """配置自有Agent后台参数 (agent-08)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可配置自有Agent")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    agent.is_owner_agent = req.is_owner_agent
    agent.auto_accept_timeout = req.auto_accept_timeout
    agent.max_concurrent = req.max_concurrent
    agent.base_price = req.base_price
    agent.daily_limit = req.daily_limit
    agent.eta_hours = req.eta_hours
    agent.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(agent)
    return agent


# ── 公共查询 ─────────────────────────────────────────────────────

@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出所有活跃Agent (需JWT用户认证)."""
    result = await db.execute(
        select(Agent)
        .where(Agent.status == "active")
        .order_by(Agent.credit_score.desc())
    )
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取Agent详情 (需JWT用户认证)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")
    return agent
