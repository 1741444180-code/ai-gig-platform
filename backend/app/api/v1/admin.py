"""管理后台API (admin-01~07)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.order import Order
from app.models.demand import Demand
from app.core.security import get_current_user
from app.services.error_handler_service import (
    initiate_arbitration,
    resolve_arbitration,
    run_all_scheduled_tasks,
)

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ── admin-01: 管理员认证中间件 ───────────────────────────────────

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员认证中间件。"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ── Schemas ──────────────────────────────────────────────────────

class UserListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


class AgentBanRequest(BaseModel):
    reason: Optional[str] = None


class OrderForceAction(BaseModel):
    action: str  # cancel | complete
    reason: str


class ArbitrationRequest(BaseModel):
    reason: str


class ArbitrationResolveRequest(BaseModel):
    resolution: str  # refund | partial_refund | release_agent | redeliver
    reason: str
    refund_amount: Optional[float] = None


class DashboardResponse(BaseModel):
    total_users: int
    total_agents: int
    total_demands: int
    total_orders: int
    today_new_demands: int
    today_new_orders: int
    completion_rate: float
    avg_price: float
    pending_arbitration: int


# ── admin-02: 用户管理 ──────────────────────────────────────────

@router.get("/users", response_model=UserListResponse)
async def admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """用户管理：分页列表+搜索。"""
    query = select(User)
    if keyword:
        query = query.where(User.phone.like(f"%{keyword}%") | User.nickname.like(f"%{keyword}%"))
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return UserListResponse(
        items=[{
            "id": u.id,
            "phone": u.phone,
            "nickname": u.nickname,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at,
        } for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/users/{user_id}/ban")
async def admin_ban_user(
    user_id: str,
    req: AgentBanRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """封禁用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.status = "banned"
    await db.commit()
    return {"success": True, "message": f"用户 {user.phone} 已封禁"}


@router.put("/users/{user_id}/unban")
async def admin_unban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """解封用户。"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.status = "active"
    await db.commit()
    return {"success": True, "message": f"用户 {user.phone} 已解封"}


# ── admin-04: Agent管理 ─────────────────────────────────────────

@router.get("/agents")
async def admin_list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Agent管理：分页列表+状态过滤。"""
    query = select(Agent)
    if status_filter:
        query = query.where(Agent.status == status_filter)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(Agent.credit_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [{
            "id": a.id,
            "name": a.name,
            "status": a.status,
            "credit_score": a.credit_score,
            "completed_count": a.completed_count,
            "is_owner_agent": a.is_owner_agent,
            "created_at": a.created_at,
        } for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.put("/agents/{agent_id}/ban")
async def admin_ban_agent(
    agent_id: str,
    req: AgentBanRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """封禁Agent。"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")
    
    agent.status = "banned"
    await db.commit()
    return {"success": True, "message": f"Agent {agent.name} 已封禁"}


# ── admin-03: 订单管理 ──────────────────────────────────────────

@router.get("/orders")
async def admin_list_orders(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """订单管理：分页列表+状态过滤。"""
    query = select(Order)
    if status_filter:
        query = query.where(Order.status == status_filter)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [{
            "id": o.id,
            "demand_id": o.demand_id,
            "agent_id": o.agent_id,
            "price": o.price,
            "status": o.status,
            "created_at": o.created_at,
        } for o in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/orders/{order_id}/force-action")
async def admin_force_order_action(
    order_id: str,
    req: OrderForceAction,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """强制取消/完成订单。"""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    if req.action == "cancel":
        order.status = "cancelled"
        order.cancel_reason = f"管理员强制取消: {req.reason}"
    elif req.action == "complete":
        order.status = "completed"
        order.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        order.accept_note = f"管理员强制完成: {req.reason}"
    else:
        raise HTTPException(status_code=400, detail="action必须是cancel或complete")
    
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    
    return {"success": True, "message": f"订单已{req.action}"}


# ── admin-05: 仲裁处理 ─────────────────────────────────────────

@router.get("/arbitration")
async def admin_list_arbitration(
    status_filter: Optional[str] = Query("pending"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """所有仲裁中订单列表。"""
    query = select(Order).where(Order.arbitration_status == status_filter)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [{
            "id": o.id,
            "status": o.status,
            "arbitration_status": o.arbitration_status,
            "reject_count": o.reject_count,
            "created_at": o.created_at,
        } for o in items],
        "total": len(items),
    }


@router.post("/arbitration/{order_id}/initiate")
async def admin_initiate_arbitration(
    order_id: str,
    req: ArbitrationRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """发起仲裁。"""
    try:
        order = await initiate_arbitration(order_id, db, req.reason)
        return {"success": True, "message": "仲裁已发起"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/arbitration/{order_id}/resolve")
async def admin_resolve_arbitration(
    order_id: str,
    req: ArbitrationResolveRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """裁决仲裁。"""
    try:
        order = await resolve_arbitration(
            order_id, db, admin.id, req.resolution, req.reason, req.refund_amount
        )
        return {"success": True, "message": f"仲裁已裁决: {req.resolution}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── admin-07: 数据看板 ─────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardResponse)
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """核心数据看板。"""
    today_start = datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0)
    
    # 总数统计
    users_count = await db.execute(select(func.count()).select_from(User))
    agents_count = await db.execute(select(func.count()).select_from(Agent))
    demands_count = await db.execute(select(func.count()).select_from(Demand))
    orders_count = await db.execute(select(func.count()).select_from(Order))
    
    # 今日新增
    today_demands = await db.execute(
        select(func.count()).select_from(Demand).where(Demand.created_at >= today_start)
    )
    today_orders = await db.execute(
        select(func.count()).select_from(Order).where(Order.created_at >= today_start)
    )
    
    # 成交率
    total_orders_result = await db.execute(select(func.count()).select_from(Order))
    total_orders = total_orders_result.scalar() or 0
    completed_orders_result = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == "completed")
    )
    completed_orders = completed_orders_result.scalar() or 0
    completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
    
    # 平均客单价
    avg_price_result = await db.execute(
        select(func.avg(Order.price)).select_from(Order).where(Order.status != "cancelled")
    )
    avg_price = avg_price_result.scalar() or 0
    
    # 待处理仲裁
    pending_arbitration_result = await db.execute(
        select(func.count()).select_from(Order).where(Order.arbitration_status == "pending")
    )
    pending_arbitration = pending_arbitration_result.scalar() or 0
    
    return DashboardResponse(
        total_users=users_count.scalar() or 0,
        total_agents=agents_count.scalar() or 0,
        total_demands=demands_count.scalar() or 0,
        total_orders=orders_count.scalar() or 0,
        today_new_demands=today_demands.scalar() or 0,
        today_new_orders=today_orders.scalar() or 0,
        completion_rate=round(completion_rate, 2),
        avg_price=round(avg_price, 2),
        pending_arbitration=pending_arbitration,
    )


# ── admin-06: 支付确认管理 ──────────────────────────────────────

from app.models.payment import Payment
from app.models.withdraw import Withdraw


@router.get("/payments")
async def admin_list_payments(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """支付记录管理列表 (admin-06)."""
    query = select(Payment)
    if status_filter:
        query = query.where(Payment.status == status_filter)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(Payment.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return {
        "items": [{
            "id": p.id,
            "order_id": p.order_id,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "status": p.status,
            "type": p.type,
            "created_at": p.created_at,
        } for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class PaymentConfirmRequest(BaseModel):
    admin_note: Optional[str] = None


@router.post("/payments/{payment_id}/confirm")
async def admin_confirm_payment(
    payment_id: str,
    req: PaymentConfirmRequest = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员确认支付 (admin-06)."""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="支付记录不存在")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="仅待确认的支付可确认")
    
    payment.status = "paid"
    payment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    
    return {"success": True, "message": "支付已确认"}


@router.post("/payments/{payment_id}/reject")
async def admin_reject_payment(
    payment_id: str,
    req: PaymentConfirmRequest = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """管理员拒绝支付 (admin-06)."""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="支付记录不存在")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="仅待确认的支付可拒绝")
    
    payment.status = "refunded"
    payment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    
    return {"success": True, "message": "支付已拒绝"}


# ── 定时任务触发 ─────────────────────────────────────────────────

@router.post("/tasks/run-scheduled")
async def admin_run_scheduled_tasks(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """手动触发定时任务（error-01超时取消 + error-09健康监控）。"""
    results = await run_all_scheduled_tasks(db)
    return {"success": True, "results": results}
