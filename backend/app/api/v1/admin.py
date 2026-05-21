from fastapi import APIRouter, Depends
from app.core.security import get_current_active_user
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User
from app.core.config import get_settings
from fastapi import HTTPException

router = APIRouter()
settings = get_settings()


@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """管理员数据看板"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    from sqlalchemy import func
    from app.models.models import Requirement, Order, Review

    # 统计概览
    total_users = (await db.execute(func.count(User.id))).scalar() or 0
    total_requirements = (await db.execute(func.count(Requirement.id))).scalar() or 0
    total_orders = (await db.execute(func.count(Order.id))).scalar() or 0
    total_completed = (await db.execute(
        func.count(Order.id)
    ).filter(Order.status == "completed")).scalar() or 0
    total_gmv = (await db.execute(
        func.sum(Order.amount)
    ).filter(Order.status.in_(["completed", "paid", "processing"]))).scalar() or 0.0

    return {
        "total_users": total_users,
        "total_requirements": total_requirements,
        "total_orders": total_orders,
        "total_completed": total_completed,
        "total_gmv": total_gmv,
    }


@router.get("/users")
async def admin_list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """用户列表"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    offset = (page - 1) * page_size
    result = await db.execute(
        User.__table__.select().order_by(User.created_at.desc()).offset(offset).limit(page_size)
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
        "page": page,
        "page_size": page_size,
    }


@router.get("/orders")
async def admin_list_orders(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """订单列表"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    from app.models.models import Order
    offset = (page - 1) * page_size
    query = Order.__table__.select().order_by(Order.created_at.desc()).offset(offset).limit(page_size)
    if status:
        query = query.where(Order.status == status)
    result = await db.execute(query)
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
        "page": page,
        "page_size": page_size,
    }


@router.get("/requirements")
async def admin_list_requirements(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """需求列表"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    from app.models.models import Requirement
    offset = (page - 1) * page_size
    query = Requirement.__table__.select().order_by(Requirement.created_at.desc()).offset(offset).limit(page_size)
    if status:
        query = query.where(Requirement.status == status)
    result = await db.execute(query)
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
        "page": page,
        "page_size": page_size,
    }
