"""需求发布 + AI结构化 + 撮合匹配 (demand-01~08, match-01~05)."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.demand import Demand
from app.models.user import User
from app.core.security import get_current_user
from app.services.ai_service import ai_extract_tags
from app.services.demand_push_service import trigger_matching

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas ──────────────────────────────────────────────────────

class DemandCreate(BaseModel):
    title: str
    description: str
    category: Optional[str] = None
    tags: Optional[str] = None
    budget: Optional[float] = None
    attachments: Optional[str] = None
    deadline: Optional[datetime] = None
    publisher_type: str = "user"
    fulfill_mode: str = "auto"


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


class DemandListResponse(BaseModel):
    items: List[DemandResponse]
    total: int
    page: int
    page_size: int


class MatchResponse(BaseModel):
    matched_count: int
    pushed_count: int
    pushed_agents: List[Dict[str, Any]]


class MatchAgentInfo(BaseModel):
    agent_id: str
    agent_name: str
    score: int
    matched_tags: List[str]


class MatchListResponse(BaseModel):
    demand_id: str
    matched_agents: List[MatchAgentInfo]
    total: int


# ── Endpoints ────────────────────────────────────────────────────

@router.post("/", response_model=DemandResponse, status_code=201)
async def create_demand(
    req: DemandCreate,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布需求 + AI自动结构化 (demand-04)."""
    ai_result = await ai_extract_tags(req.description)
    ai_structured = json.dumps(ai_result, ensure_ascii=False)
    
    demand = Demand(
        user_id=current_user.id,
        title=req.title,
        description=req.description,
        category=req.category or ai_result.get("category"),
        tags=req.tags or json.dumps(ai_result.get("tags", []), ensure_ascii=False),
        budget=req.budget,
        attachments=req.attachments,
        deadline=req.deadline,
        publisher_type=req.publisher_type,
        fulfill_mode=req.fulfill_mode,
        ai_structured=ai_structured,
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)
    
    # 后台触发撮合
    bg.add_task(_do_match, demand.id)
    
    return demand


@router.get("/", response_model=DemandListResponse)
async def list_demands(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_budget: Optional[float] = Query(None),
    max_budget: Optional[float] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """需求列表 + 筛选 (demand-05)."""
    query = select(Demand)
    
    if category:
        query = query.where(Demand.category == category)
    if status:
        query = query.where(Demand.status == status)
    else:
        query = query.where(Demand.status.in_(["open", "quoted", "matched"]))
    if min_budget is not None:
        query = query.where(Demand.budget >= min_budget)
    if max_budget is not None:
        query = query.where(Demand.budget <= max_budget)
    if keyword:
        query = query.where(Demand.title.ilike(f"%{keyword}%") | Demand.description.ilike(f"%{keyword}%"))
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(Demand.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return DemandListResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{demand_id}", response_model=DemandResponse)
async def get_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """需求详情 (含AI结构化结果) (demand-06)."""
    result = await db.execute(select(Demand).where(Demand.id == demand_id))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    return demand


@router.put("/{demand_id}", response_model=DemandResponse)
async def update_demand(
    demand_id: str,
    req: DemandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """编辑需求 (demand-07): 仅open状态可编辑."""
    result = await db.execute(select(Demand).where(Demand.id == demand_id))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    if demand.status != "open":
        raise HTTPException(status_code=400, detail="仅开放状态的需求可编辑")
    if demand.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己的需求")
    
    ai_result = await ai_extract_tags(req.description)
    
    demand.title = req.title
    demand.description = req.description
    demand.category = req.category or ai_result.get("category")
    demand.tags = req.tags or json.dumps(ai_result.get("tags", []), ensure_ascii=False)
    demand.budget = req.budget
    demand.attachments = req.attachments
    demand.deadline = req.deadline
    demand.ai_structured = json.dumps(ai_result, ensure_ascii=False)
    demand.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(demand)
    return demand


@router.post("/{demand_id}/cancel", response_model=DemandResponse)
async def cancel_demand(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消需求 (demand-08): 仅open状态可取消."""
    result = await db.execute(select(Demand).where(Demand.id == demand_id))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    if demand.status != "open":
        raise HTTPException(status_code=400, detail="仅开放状态的需求可取消")
    if demand.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能取消自己的需求")
    
    demand.status = "cancelled"
    demand.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(demand)
    return demand


# ── 撮合匹配 (match-01~05) ──────────────────────────────────────

@router.post("/{demand_id}/match", response_model=MatchResponse)
async def trigger_demand_match(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动触发需求撮合 (match-05)."""
    result = await db.execute(select(Demand).where(Demand.id == demand_id))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    if demand.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能匹配自己的需求")
    if demand.status != "open":
        raise HTTPException(status_code=400, detail="仅开放状态的需求可匹配")
    
    return await trigger_matching(demand, db)


@router.get("/{demand_id}/matching", response_model=MatchListResponse)
async def get_matched_agents(
    demand_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看需求匹配的Agent列表 (match-05)."""
    result = await db.execute(select(Demand).where(Demand.id == demand_id))
    demand = result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="需求不存在")
    
    from app.services.match_service import match_agents
    matched = await match_agents(demand, db, top_n=5)
    
    return MatchListResponse(
        demand_id=demand.id,
        matched_agents=[
            MatchAgentInfo(
                agent_id=item["agent"].id,
                agent_name=item["agent"].name,
                score=item["score"],
                matched_tags=item["matched_tags"],
            )
            for item in matched
        ],
        total=len(matched),
    )


async def _do_match(demand_id: str):
    """后台任务：触发撮合."""
    try:
        from app.db.engine import get_db as _get_db
        async for db in _get_db():
            result = await db.execute(select(Demand).where(Demand.id == demand_id))
            demand = result.scalar_one_or_none()
            if demand and demand.status == "open":
                await trigger_matching(demand, db)
    except Exception as e:
        logger.error(f"[Match] Background matching failed for {demand_id}: {e}")
