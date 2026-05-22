"""管理后台 API — 数据看板、用户管理、订单管理、需求管理"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import User, Requirement, Order, Review, Payment, WebhookLog

router = APIRouter()


async def _get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """校验管理员权限的依赖"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.get("/dashboard", summary="管理员数据看板")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(_get_current_admin_user),
):
    """数据看板：用户数 / 需求数 / 订单数 / GMV"""
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    total_requirements = (await db.execute(select(func.count()).select_from(Requirement))).scalar() or 0
    total_orders = (await db.execute(select(func.count()).select_from(Order))).scalar() or 0
    total_completed = (await db.execute(
        select(func.count()).select_from(Order).where(Order.status == "completed")
    )).scalar() or 0
    total_gmv = (await db.execute(
        select(func.coalesce(func.sum(Order.amount), 0.0))
        .select_from(Order)
        .where(Order.status.in_(["completed", "paid", "processing"]))
    )).scalar() or 0.0

    return {
        "total_users": total_users,
        "total_requirements": total_requirements,
        "total_orders": total_orders,
        "total_completed": total_completed,
        "total_gmv": round(float(total_gmv), 2),
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

    base_where = [Order.status == status] if status else []

    total_result = await db.execute(
        select(func.count()).select_from(Order).where(*base_where) if base_where else select(func.count()).select_from(Order)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Order)
        .where(*base_where)
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

    base_where = Requirement.status == status if status else True

    total_result = await db.execute(
        select(func.count()).select_from(Requirement).where(base_where)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Requirement)
        .where(base_where)
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
    """分页查看 Webhook 推送记录，支持按 status 过滤"""
    offset = (page - 1) * page_size

    base_where = WebhookLog.status == status if status else True

    total_result = await db.execute(
        select(func.count()).select_from(WebhookLog).where(base_where)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(WebhookLog)
        .where(base_where)
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
