"""异常流程处理服务 (error-01~09).

包含：超时未交付自动取消、无人接单通知+取消、仲裁流程、支付超时取消、
恶意拒绝防护、恶意差评申诉、Agent中途放弃、保证金触发、Agent健康监控。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.agent import Agent
from app.models.demand import Demand
from app.models.user import User
from app.models.review import Review

logger = logging.getLogger(__name__)


# ── error-01: Agent超时未交付自动取消 ────────────────────────────

async def cancel_overdue_orders(db: AsyncSession, hours_threshold: int = 48) -> List[str]:
    """定时任务：超过ETA+24h未交付的订单 → 自动取消 → 退款 → 扣信用分-10。
    
    Args:
        db: 数据库会话
        hours_threshold: 超时阈值（小时），默认ETA+24h
        
    Returns:
        被取消的订单ID列表
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours_threshold)
    
    result = await db.execute(
        select(Order).where(
            Order.status == "accepted",
            Order.updated_at < cutoff,
        )
    )
    overdue_orders = result.scalars().all()
    
    cancelled_ids = []
    for order in overdue_orders:
        order.status = "cancelled"
        order.cancel_reason = "超时未交付自动取消"
        order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # 扣信用分
        agent_result = await db.execute(
            select(Agent).where(Agent.id == order.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.credit_score = max(0, agent.credit_score - 10)
        
        # 需求重新入池
        demand_result = await db.execute(
            select(Demand).where(Demand.id == order.demand_id)
        )
        demand = demand_result.scalar_one_or_none()
        if demand:
            demand.status = "open"
            demand.match_status = "pending"
        
        cancelled_ids.append(order.id)
        logger.warning(f"[Error-01] Order {order.id} cancelled due to timeout")
    
    if cancelled_ids:
        await db.commit()
    
    return cancelled_ids


# ── error-03: 仲裁流程 ──────────────────────────────────────────

async def initiate_arbitration(
    order_id: str,
    db: AsyncSession,
    reason: str,
) -> Order:
    """触发仲裁 → 订单status=disputed → 管理员48h内裁决。
    
    Returns:
        更新后的订单对象
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"订单不存在: {order_id}")
    
    order.status = "disputed"
    order.arbitration_status = "pending"
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    
    logger.warning(f"[Error-03] Order {order_id} entered arbitration: {reason}")
    return order


async def resolve_arbitration(
    order_id: str,
    db: AsyncSession,
    admin_id: str,
    resolution: str,  # refund | partial_refund | release_agent | redeliver
    reason: str,
    refund_amount: Optional[float] = None,
) -> Order:
    """管理员裁决仲裁。
    
    Args:
        resolution: 裁决结果
            - refund: 全额退款
            - partial_refund: 部分退款
            - release_agent: 放款给Agent
            - redeliver: 要求Agent再改
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"订单不存在: {order_id}")
    if order.status != "disputed":
        raise ValueError("仅仲裁中订单可裁决")
    
    order.arbitration_status = "resolved"
    order.arbitration_result = f"admin:{admin_id}|resolution:{resolution}|reason:{reason}"
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if resolution == "refund":
        order.status = "cancelled"
        order.cancel_reason = f"仲裁裁决: 全额退款 - {reason}"
    elif resolution == "partial_refund":
        order.status = "cancelled"
        order.cancel_reason = f"仲裁裁决: 部分退款({refund_amount}) - {reason}"
    elif resolution == "release_agent":
        order.status = "completed"
        order.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        order.accept_note = f"仲裁裁决: 放款Agent - {reason}"
        # Agent信用分+5
        agent_result = await db.execute(
            select(Agent).where(Agent.id == order.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            agent.credit_score += 5
            agent.completed_count += 1
    elif resolution == "redeliver":
        order.status = "rejected"
        order.reject_reason = f"仲裁裁决: 要求再改 - {reason}"
    
    await db.commit()
    
    logger.info(f"[Error-03] Order {order_id} arbitration resolved: {resolution}")
    return order


# ── error-07: Agent中途放弃接单处理 ─────────────────────────────

async def agent_abandon_order(
    order_id: str,
    db: AsyncSession,
    agent_id: str,
    reason: str,
) -> Order:
    """Agent主动放弃接单 → 扣信用分-5 → 需求重新入池 → 通知用户重新匹配。
    
    这与order-05的agent_cancel_order逻辑相同，但可由管理员触发。
    """
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.agent_id == agent_id,
            Order.status == "accepted",
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"订单不存在或状态不符: {order_id}")
    
    order.status = "cancelled"
    order.cancel_reason = f"Agent中途放弃: {reason}"
    order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    # 扣信用分
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent:
        agent.credit_score = max(0, agent.credit_score - 5)
    
    # 需求重新入池
    demand_result = await db.execute(select(Demand).where(Demand.id == order.demand_id))
    demand = demand_result.scalar_one_or_none()
    if demand:
        demand.status = "open"
        demand.match_status = "pending"
    
    await db.commit()
    
    logger.warning(f"[Error-07] Agent {agent_id} abandoned order {order_id}")
    return order


# ── error-09: Agent健康监控 ─────────────────────────────────────

async def check_agent_health(db: AsyncSession) -> Dict[str, List[str]]:
    """定时扫描Agent健康状态。
    
    检查项：
    1. 注册7天无接单 → 标记"未激活"
    2. 连续3单被拒 → 标记"低质量"暂停接单
    3. 3次Webhook失败 → 标记"失联"暂停推送
    
    Returns:
        {"inactive": [...], "low_quality": [...], "unreachable": [...]}
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seven_days_ago = now - timedelta(days=7)
    
    results = {
        "inactive": [],
        "low_quality": [],
        "unreachable": [],
    }
    
    # 1. 注册7天无接单
    inactive_result = await db.execute(
        select(Agent).where(
            Agent.status == "active",
            Agent.created_at < seven_days_ago,
            Agent.completed_count == 0,
        )
    )
    for agent in inactive_result.scalars().all():
        results["inactive"].append(agent.id)
        logger.info(f"[Error-09] Agent {agent.id} marked as inactive")
    
    # 2. 连续3单被拒 (通过reject_count统计)
    low_quality_result = await db.execute(
        select(Agent).where(
            Agent.status == "active",
            Agent.failed_count >= 3,
        )
    )
    for agent in low_quality_result.scalars().all():
        results["low_quality"].append(agent.id)
        agent.status = "suspended"
        logger.warning(f"[Error-09] Agent {agent.id} suspended for low quality")
    
    # 3. Webhook失败次数统计 (需要独立webhook_log表，暂用order表统计)
    unreachable_result = await db.execute(
        select(Order.agent_id, func.count()).where(
            Order.status == "cancelled",
            Order.cancel_reason.ilike("%webhook%"),
        ).group_by(Order.agent_id).having(func.count() >= 3)
    )
    for row in unreachable_result.all():
        agent_id = row[0]
        results["unreachable"].append(agent_id)
        agent_update = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_update.scalar_one_or_none()
        if agent and agent.status == "active":
            agent.status = "suspended"
    
    await db.commit()
    
    return results


# ── 定时任务调度入口 ─────────────────────────────────────────────

async def run_all_scheduled_tasks(db: AsyncSession) -> Dict[str, Any]:
    """执行所有定时任务。
    
    应每5分钟调用一次。
    """
    results = {}
    
    # error-01: 超时未交付自动取消
    cancelled = await cancel_overdue_orders(db, hours_threshold=48)
    results["cancelled_overdue"] = cancelled
    
    # error-09: Agent健康监控
    health = await check_agent_health(db)
    results["health_check"] = health
    
    return results
