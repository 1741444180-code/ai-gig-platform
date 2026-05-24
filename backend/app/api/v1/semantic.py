"""Semantic match API endpoints (vector-06)."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.user import User
from app.models.demand import Demand
from app.models.agent import Agent
from app.core.security import get_current_user
from app.services.agent_key_service import get_current_agent
from app.services.semantic_match_service import (
    semantic_match_agents,
    vectorize_demand,
    vectorize_agent,
)

router = APIRouter(prefix="/semantic", tags=["语义匹配"])


class SemanticMatchAgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    score: float
    similarity: float


class SemanticMatchResponse(BaseModel):
    demand_id: str
    matched_agents: List[SemanticMatchAgentResponse]
    total: int


@router.get("/demands/{demand_id}/semantic-match", response_model=SemanticMatchResponse)
async def get_semantic_match(
    demand_id: str,
    top_n: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语义匹配查询 (vector-06).
    
    返回语义匹配Top N Agent列表+匹配得分。
    """
    # 检查需求
    from sqlalchemy import select
    result = await db.execute(
        select(Demand).where(
            Demand.id == demand_id,
            Demand.user_id == current_user.id,
        )
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    # 如果需求没有向量，先生成
    if not demand.demand_vec:
        await vectorize_demand(demand, db)
    
    # 语义匹配
    matched = await semantic_match_agents(demand, db, top_n=top_n)
    
    return SemanticMatchResponse(
        demand_id=demand.id,
        matched_agents=[
            SemanticMatchAgentResponse(
                agent_id=item["agent"].id,
                agent_name=item["agent"].name,
                score=item["score"],
                similarity=item["similarity"],
            )
            for item in matched
        ],
        total=len(matched),
    )


@router.post("/agents/{agent_id}/vectorize")
async def trigger_agent_vectorize(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """手动触发Agent向量化 (vector-03)."""
    from sqlalchemy import select
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")
    
    await vectorize_agent(agent, db)
    
    return {"success": True, "message": "Agent向量化完成"}


@router.post("/demands/{demand_id}/vectorize")
async def trigger_demand_vectorize(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发需求向量化 (vector-04)."""
    from sqlalchemy import select
    result = await db.execute(
        select(Demand).where(
            Demand.id == demand_id,
            Demand.user_id == current_user.id,
        )
    )
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    await vectorize_demand(demand, db)
    
    return {"success": True, "message": "需求向量化完成"}
