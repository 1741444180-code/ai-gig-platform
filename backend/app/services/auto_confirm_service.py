"""超时自动确认服务

处理 delivered 状态超过指定时长（默认48h）未确认的订单，
自动执行确认验收流程。
"""

from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Order,
    Requirement,
    User,
    CreditRecord,
)


async def _update_credit_score(
    user_id,
    db: AsyncSession,
    change: int,
    reason: str,
    order_id=None,
):
    """更新用户信誉分（内部辅助函数）

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

    record = CreditRecord(
        user_id=user_id,
        order_id=order_id,
        change=change,
        reason=reason,
        before_score=before,
        after_score=after,
    )
    db.add(record)


async def auto_confirm_expired_orders(
    db: AsyncSession, hours: int = 48
) -> dict:
    """自动确认超过指定时长未处理的 delivered 订单

    查询所有 delivered 状态且 delivered_at 超过 hours 的订单，
    自动执行确认验收流程：
    1. 订单状态改为 completed
    2. user_confirm 标记为 1
    3. 记录 completed_at
    4. 需求方 +5 信誉分，Agent +5 信誉分
    5. 关联需求状态改为 completed

    Args:
        db: 数据库会话
        hours: 超时阈值（小时），默认48小时

    Returns:
        dict: {
            "confirmed_count": 确认数量,
            "orders": [{"id": "...", "amount": ...}, ...]
        }
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    # 查询所有 delivered 状态且 delivered_at 超过阈值的订单
    result = await db.execute(
        select(Order).where(
            Order.status == "delivered",
            Order.completed_at.is_(None),
            # 使用 created_at 作为基准（MVP 阶段无 delivered_at 字段）
            Order.created_at <= cutoff_time,
        )
    )
    expired_orders = result.scalars().all()

    if not expired_orders:
        return {"confirmed_count": 0, "orders": []}

    confirmed = []
    for order in expired_orders:
        # 更新订单状态
        order.status = "completed"
        order.user_confirm = 1
        order.completed_at = datetime.now(timezone.utc)
        order.delivery_message = (
            (order.delivery_message or "")
            + f"\n[系统自动确认] delivered 状态超过 {hours}h 未处理"
        )

        # 更新关联需求状态
        req_result = await db.execute(
            select(Requirement).where(Requirement.id == order.requirement_id)
        )
        requirement = req_result.scalar_one_or_none()
        if requirement:
            requirement.status = "completed"

        # 信誉分：需求方 +5
        await _update_credit_score(
            order.user_id,
            db,
            change=5,
            reason=f"订单超时 {hours}h 自动确认验收",
            order_id=order.id,
        )

        # 信誉分：Agent +5
        await _update_credit_score(
            order.agent_id,
            db,
            change=5,
            reason=f"订单超时 {hours}h 自动确认交付",
            order_id=order.id,
        )

        confirmed.append(
            {
                "id": str(order.id),
                "amount": order.amount,
                "user_id": str(order.user_id),
                "agent_id": str(order.agent_id),
            }
        )

    await db.flush()

    return {
        "confirmed_count": len(confirmed),
        "orders": confirmed,
    }
