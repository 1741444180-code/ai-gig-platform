"""Order API endpoints — Agent接单/交付/取消 + 用户查看 (order-02~07)."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.order import Order
from app.models.agent import Agent
from app.models.demand import Demand
from app.models.user import User
from app.schemas.order import (
    AgentQuoteRequest,
    AgentDeliverRequest,
    AgentCancelRequest,
    OrderResponse,
    OrderListResponse,
)
from app.core.security import get_current_user
from app.services.agent_key_service import get_current_agent

router = APIRouter()

# 平台抽成比例 (10%)
PLATFORM_FEE_RATE = 0.10


# ── Agent接单 (order-02) ─────────────────────────────────────────

@router.post("/accept", response_model=OrderResponse)
async def agent_accept_order(
    req: AgentQuoteRequest,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent接单 (order-02).

    Agent通过API Key认证后，接受已匹配的需求 → 创建订单。
    """
    # 查找匹配的pending订单
    result = await db.execute(
        select(Order).where(
            Order.agent_id == agent.id,
            Order.status == "pending",
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="没有待接的订单")

    # 检查并发限制
    active_count_result = await db.execute(
        select(func.count()).select_from(
            select(Order).where(
                Order.agent_id == agent.id,
                Order.status.in_(["accepted", "delivering", "delivered"]),
            ).subquery()
        )
    )
    active_count = active_count_result.scalar() or 0
    if active_count >= agent.max_concurrent:
        raise HTTPException(
            status_code=429,
            detail=f"已达最大并发接单数 {agent.max_concurrent}",
        )

    # 更新订单
    order.status = "accepted"
    order.price = req.price
    order.platform_fee = req.price * PLATFORM_FEE_RATE if not agent.is_owner_agent else 0.0
    order.deposit = 0.0  # MVP免费试用
    order.eta_hours = req.eta_hours or agent.eta_hours
    order.accept_note = req.accept_note
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(order)

    return order


# ── Agent交付 (order-03) ─────────────────────────────────────────

@router.post("/deliver", response_model=OrderResponse)
async def agent_deliver_order(
    req: AgentDeliverRequest,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent交付订单 (order-03).

    接收content+attachments+message → status accepted→delivered。
    """
    # 查找进行中的订单
    result = await db.execute(
        select(Order).where(
            Order.agent_id == agent.id,
            Order.status == "accepted",
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="没有进行中的订单")

    order.status = "delivered"
    order.delivery_url = req.delivery_url
    order.delivery_note = req.delivery_note
    order.delivery_attempts += 1
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(order)

    return order


# ── Agent主动取消 (order-05) ──────────────────────────────────────

@router.post("/cancel", response_model=OrderResponse)
async def agent_cancel_order(
    req: AgentCancelRequest,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent主动取消接单 (order-05).

    状态回退accepted→cancelled → 扣信用分-5 → 需求重新进入待接单池。
    """
    result = await db.execute(
        select(Order).where(
            Order.agent_id == agent.id,
            Order.status == "accepted",
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="没有进行中的订单")

    order.status = "cancelled"
    order.cancel_reason = req.cancel_reason
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # 扣信用分
    agent.credit_score = max(0, agent.credit_score - 5)

    # 需求重新进入待接单池
    demand_result = await db.execute(
        select(Demand).where(Demand.id == order.demand_id)
    )
    demand = demand_result.scalar_one_or_none()
    if demand:
        demand.status = "open"
        demand.match_status = "pending"

    await db.commit()
    await db.refresh(order)

    return order


# ── Agent查询订单 (order-04) ─────────────────────────────────────

@router.get("/my", response_model=OrderListResponse)
async def agent_list_orders(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent查看自己的订单列表 (order-04)."""
    query = select(Order).where(Order.agent_id == agent.id)

    if status_filter:
        query = query.where(Order.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return OrderListResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/my/{order_id}", response_model=OrderResponse)
async def agent_get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent查看订单详情 (order-04)."""
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.agent_id == agent.id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


# ── 用户端查看订单 (order-06) ─────────────────────────────────────

@router.get("/{order_id}", response_model=OrderResponse)
async def user_get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户查看订单详情 (order-06)."""
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.get("/", response_model=OrderListResponse)
async def user_list_orders(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户查看自己的订单列表 (order-06)."""
    query = select(Order).where(Order.user_id == current_user.id)

    if status_filter:
        query = query.where(Order.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return OrderListResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
    )
