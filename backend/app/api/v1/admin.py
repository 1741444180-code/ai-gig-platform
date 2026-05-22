"""管理后台 API — 数据看板、用户管理、订单管理、需求管理、支付统计"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import User, Requirement, Order, Review, Payment, WebhookLog
from app.services.auto_confirm_service import auto_confirm_expired_orders

router = APIRouter()


async def _get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """校验管理员权限的依赖"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def _make_where(model, status: str | None):
    """安全构建 status 过滤条件"""
    return [model.status == status] if status else []


@router.get("/dashboard", summary="管理员数据看板")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """数据看板：用户/需求/订单/GMV/支付"""
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_requirements = (await db.execute(select(func.count()).select_from(Requirement))).scalar() or 0
    total_orders = (await db.execute(select(func.count()).select_from(Order))).scalar() or 0
    total_completed = (await db.execute(
        select(func.count()).select_from(Order).where(Order.status == "completed")
    )).scalar() or 0

    gmv_where = Order.status.in_(["completed", "paid", "processing"])
    total_gmv = (await db.execute(
        select(func.coalesce(func.sum(Order.amount), 0.0))
        .select_from(Order)
        .where(gmv_where)
    )).scalar() or 0.0

    paid_payments = (await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0.0))
        .select_from(Payment)
        .where(Payment.status == "paid", Payment.type == "payment")
    )).scalar() or 0.0

    return {
        "total_users": total_users,
        "total_requirements": total_requirements,
        "total_orders": total_orders,
        "total_completed": total_completed,
        "total_gmv": round(float(total_gmv), 2),
        "total_paid": round(float(paid_payments), 2),
    }


@router.get("/users", summary="用户列表")
async def admin_list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """分页查看所有用户"""
    offset = (page - 1) * page_size

    total_result = await db.execute(select(func.count()).select_from(User))
    total = total_result.scalar() or 0

    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(u.id),
                "nickname": u.nickname,
                "phone": u.phone,
                "role": u.role,
                "status": u.status,
                "credit_score": u.credit_score,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/orders", summary="订单列表")
async def admin_list_orders(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """分页查看所有订单"""
    offset = (page - 1) * page_size
    where_clause = _make_where(Order, status)

    total_result = await db.execute(
        select(func.count()).select_from(Order).where(*where_clause)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Order)
        .where(*where_clause)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    orders = result.scalars().all()

    return {
        "orders": [
            {
                "id": str(o.id),
                "amount": o.amount,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/requirements", summary="需求列表")
async def admin_list_requirements(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """分页查看所有需求"""
    offset = (page - 1) * page_size
    where_clause = _make_where(Requirement, status)

    total_result = await db.execute(
        select(func.count()).select_from(Requirement).where(*where_clause)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Requirement)
        .where(*where_clause)
        .order_by(Requirement.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    requirements = result.scalars().all()

    return {
        "requirements": [
            {
                "id": str(r.id),
                "title": r.title,
                "category": r.category,
                "status": r.status,
                "budget": r.budget,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in requirements
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/webhooks", summary="Webhook 推送记录列表")
async def admin_list_webhooks(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """分页查看 Webhook 推送记录"""
    offset = (page - 1) * page_size
    where_clause = _make_where(WebhookLog, status)

    total_result = await db.execute(
        select(func.count()).select_from(WebhookLog).where(*where_clause)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(WebhookLog)
        .where(*where_clause)
        .order_by(WebhookLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "webhooks": [
            {
                "id": str(w.id),
                "agent_id": str(w.agent_id),
                "event_type": w.event_type,
                "order_id": str(w.order_id) if w.order_id else None,
                "webhook_url": w.webhook_url,
                "status": w.status,
                "attempts": w.attempts,
                "last_error": w.last_error,
                "idempotency_key": w.idempotency_key,
                "response_code": w.response_code,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/auto-confirm", summary="超时自动确认验收")
async def admin_auto_confirm(
    hours: int = Query(48, ge=1, description="超时阈值（小时），默认48小时"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """手动触发超时自动确认验收

    扫描所有 delivered 状态超过指定时长未处理的订单，自动确认。
    """
    result = await auto_confirm_expired_orders(db, hours=hours)
    return {
        "message": "自动确认完成",
        "hours": hours,
        "confirmed_count": result["confirmed_count"],
        "orders": result["orders"],
    }
