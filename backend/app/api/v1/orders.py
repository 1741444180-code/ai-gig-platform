"""订单管理 API

提供需求方视角的订单查询、验收、担保交易等核心功能。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import (
    AgentProfile,
    CreditRecord,
    Order,
    Requirement,
    User,
)
from app.schemas.order import (
    OrderResponse,
    OrderListResponse,
    OrderStatusResponse,
)

router = APIRouter()


# ==================== 工具函数 ====================


async def _get_order_with_auth(
    order_id: str,
    current_user: User,
    db: AsyncSession,
    allowed_user_ids: list[str] | None = None,
) -> Order:
    """获取订单并校验权限

    只有订单相关用户（需求方或Agent）才能查看/操作。

    Args:
        order_id: 订单ID
        current_user: 当前用户
        db: 数据库会话
        allowed_user_ids: 可选的额外允许查看的用户ID列表（如admin）

    Returns:
        Order 对象

    Raises:
        HTTPException: 订单不存在或无权访问
    """
    import uuid as _uuid

    try:
        oid = _uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的订单ID格式",
        )

    result = await db.execute(select(Order).where(Order.id == oid))
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        )

    # 权限校验：需求方或Agent本人
    user_id_str = str(current_user.id)
    if allowed_user_ids and user_id_str in allowed_user_ids:
        return order
    if str(order.user_id) != user_id_str and str(order.agent_id) != user_id_str:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该订单",
        )
    return order


async def _update_credit_score(
    user_id,
    db: AsyncSession,
    change: int,
    reason: str,
    order_id=None,
):
    """更新用户信誉分

    Args:
        user_id: 用户ID
        db: 数据库会话
        change: 分数变化（正/负）
        reason: 变化原因
        order_id: 关联订单ID（可选）
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return

    before = user.credit_score
    user.credit_score = max(0, user.credit_score + change)  # 最低0分
    after = user.credit_score

    # 写入信誉记录
    record = CreditRecord(
        user_id=user_id,
        order_id=order_id,
        change=change,
        reason=reason,
        before_score=before,
        after_score=after,
    )
    db.add(record)


# ==================== 订单查询API ====================


@router.get("/", response_model=OrderListResponse, summary="获取我的订单列表")
async def list_my_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: str | None = Query(None, description="按状态过滤"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的订单列表（需求方视角）

    返回当前用户作为需求方创建的订单列表。
    """
    query = select(Order).where(Order.user_id == current_user.id)
    count_query = select(func.count()).select_from(Order).where(
        Order.user_id == current_user.id
    )

    if status_filter:
        query = query.where(Order.status == status_filter)
        count_query = count_query.where(Order.status == status_filter)

    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    orders_result = await db.execute(query)
    orders = orders_result.scalars().all()

    return OrderListResponse(
        total=total,
        items=[OrderResponse.model_validate(o) for o in orders],
    )


@router.get("/{order_id}", response_model=OrderResponse, summary="获取订单详情")
async def get_order_detail(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取订单详情

    仅订单相关用户（需求方或Agent）可查看。
    """
    order = await _get_order_with_auth(order_id, current_user, db)
    return OrderResponse.model_validate(order)


@router.get("/{order_id}/status", response_model=OrderStatusResponse, summary="查询订单状态")
async def get_order_status(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """查询订单状态

    返回订单的核心状态信息（轻量接口）。
    """
    order = await _get_order_with_auth(order_id, current_user, db)
    return OrderStatusResponse(
        id=order.id,
        status=order.status,
        modify_count=order.modify_count,
        ai_review_score=order.ai_review_score,
        user_confirm=order.user_confirm,
        completed_at=order.completed_at,
    )


# ==================== 验收交付API（需求方操作） ====================


@router.post("/{order_id}/confirm", summary="确认验收")
async def confirm_order(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """需求方确认验收

    1. 验证订单归属（仅需求方可操作）
    2. 订单状态改为 completed
    3. 更新双方信誉分（需求方+5，Agent+5）
    4. 记录完成时间
    """
    order = await _get_order_with_auth(order_id, current_user, db)

    # 仅需求方可确认验收
    if str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅需求方可确认验收",
        )

    # 状态校验
    if order.status not in ("delivered", "reviewing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前订单状态为「{order.status}」，无法确认验收",
        )

    # 更新订单
    order.status = "completed"
    order.user_confirm = 1
    order.completed_at = datetime.now(timezone.utc)

    # 信誉分：需求方完成+5
    await _update_credit_score(
        order.user_id, db, change=5, reason="完成订单确认验收", order_id=order.id
    )

    # 信誉分：Agent完成+5
    await _update_credit_score(
        order.agent_id, db, change=5, reason="完成订单交付", order_id=order.id
    )

    # 更新需求状态
    req_result = await db.execute(
        select(Requirement).where(Requirement.id == order.requirement_id)
    )
    requirement = req_result.scalar_one_or_none()
    if requirement:
        requirement.status = "completed"

    await db.flush()

    return {
        "message": "验收确认成功",
        "order_id": str(order.id),
        "status": "completed",
        "completed_at": order.completed_at.isoformat(),
    }


from pydantic import BaseModel, Field

class RejectOrderRequest(BaseModel):
    reason: str = Field(..., description="拒绝原因", max_length=500)


@router.post("/{order_id}/reject", summary="拒绝验收")
async def reject_order(
    order_id: str,
    body: RejectOrderRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """需求方拒绝验收

    1. 验证订单归属（仅需求方可操作）
    2. modify_count+1
    3. 如果超过最大修改次数，自动确认验收
    4. 如果非Agent责任，需求方信誉分-2
    5. 状态改回 processing（Agent需重新交付）
    """
    from app.core.config import get_settings

    settings = get_settings()
    order = await _get_order_with_auth(order_id, current_user, db)

    # 仅需求方可拒绝验收
    if str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅需求方可拒绝验收",
        )

    # 状态校验
    if order.status not in ("delivered", "reviewing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前订单状态为「{order.status}」，无法拒绝验收",
        )

    order.modify_count += 1

    # 检查是否超过最大修改次数
    if order.modify_count >= settings.MAX_MODIFY_TIMES:
        # 超过最大修改次数，自动确认
        order.status = "completed"
        order.user_confirm = 1
        order.completed_at = datetime.now(timezone.utc)
        order.delivery_message = (
            (order.delivery_message or "")
            + f"\n[自动确认] 已达最大修改次数({settings.MAX_MODIFY_TIMES})次"
        )

        # 更新需求状态
        req_result = await db.execute(
            select(Requirement).where(Requirement.id == order.requirement_id)
        )
        requirement = req_result.scalar_one_or_none()
        if requirement:
            requirement.status = "completed"

        # 信誉分更新：超时/达上限自动确认，双方各+5
        await _update_credit_score(
            order.user_id, db, change=5, reason="完成订单确认验收（达修改上限）", order_id=order.id
        )
        await _update_credit_score(
            order.agent_id, db, change=5, reason="完成订单交付（达修改上限）", order_id=order.id
        )

        await db.flush()

        return {
            "message": f"已达最大修改次数（{settings.MAX_MODIFY_TIMES}次），自动确认验收",
            "order_id": str(order.id),
            "status": "completed",
            "modify_count": order.modify_count,
        }

    # 未超过最大修改次数，退回给Agent重新处理
    order.status = "processing"
    order.user_confirm = 0

    # 拒绝验收视为 Agent 交付质量问题，Agent 信誉分 -2
    await _update_credit_score(
        order.agent_id,
        db,
        change=-2,
        reason=f"订单验收被拒绝（第{order.modify_count}次修改）",
        order_id=order.id,
    )

    await db.flush()

    return {
        "message": "已拒绝验收，退回给Agent重新处理",
        "order_id": str(order.id),
        "status": "processing",
        "modify_count": order.modify_count,
        "remaining_modifies": settings.MAX_MODIFY_TIMES - order.modify_count,
    }
