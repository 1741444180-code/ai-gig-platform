"""Webhook 推送服务 — 需求推送 + 重试机制 + 幂等性

负责将新需求推送给匹配到的 Agent，支持：
- HTTP POST 推送到 Agent webhook_url
- 5 次重试，延迟递增（2s → 4s → 8s → 16s → 32s）
- 幂等性 Key 防止重复处理
- 推送结果记录到数据库 WebhookLog 表
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WebhookLog
from app.services.api_key_service import (
    WEBHOOK_RETRY_CONFIG,
    get_webhook_idempotency_key,
    get_webhook_retry_delay,
)

logger = logging.getLogger(__name__)


async def push_demand_to_agent(
    webhook_url: str,
    payload: dict,
    order_id: str,
    agent_id: UUID,
    event_type: str = "demand_pushed",
    db: Optional[AsyncSession] = None,
    max_retries: int = WEBHOOK_RETRY_CONFIG["max_retries"],
) -> dict:
    """推送需求给 Agent

    Args:
        webhook_url: Agent 的回调地址
        payload: 推送数据（需求信息）
        order_id: 订单/需求 ID（用于幂等性）
        agent_id: Agent 用户 ID
        event_type: 事件类型
        db: 数据库会话（可选，用于写入推送日志）
        max_retries: 最大重试次数

    Returns:
        推送结果: {success, attempts, last_status, last_error, log_id}
    """
    result: dict = {
        "success": False,
        "attempts": 0,
        "last_status": 0,
        "last_error": None,
        "log_id": None,
    }

    # 用于记录最后一次响应的详情
    last_response_body: Optional[str] = None

    for attempt in range(max_retries):
        idempotency_key = get_webhook_idempotency_key(webhook_url, order_id, attempt)

        headers = {
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
            "X-Webhook-Event": event_type,
            "X-Webhook-Attempt": str(attempt + 1),
        }

        try:
            async with httpx.AsyncClient(
                timeout=WEBHOOK_RETRY_CONFIG["timeout_seconds"]
            ) as client:
                resp = await client.post(webhook_url, json=payload, headers=headers)
                result["attempts"] = attempt + 1
                result["last_status"] = resp.status_code
                last_response_body = resp.text[:1000]

                if resp.status_code == 200:
                    result["success"] = True
                    logger.info(
                        f"Webhook 推送成功: url={webhook_url}, "
                        f"order_id={order_id}, attempt={attempt + 1}"
                    )
                    # 写入成功日志
                    if db:
                        log_record = WebhookLog(
                            agent_id=agent_id,
                            event_type=event_type,
                            order_id=_parse_uuid(order_id),
                            webhook_url=webhook_url,
                            payload=payload,
                            status="success",
                            attempts=attempt + 1,
                            idempotency_key=idempotency_key,
                            response_code=resp.status_code,
                            response_body=last_response_body,
                        )
                        db.add(log_record)
                        await db.flush()
                        await db.refresh(log_record)
                        result["log_id"] = str(log_record.id)
                    return result
                else:
                    result["last_error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        f"Webhook 推送失败 (尝试 {attempt + 1}/{max_retries}): "
                        f"status={resp.status_code}, url={webhook_url}"
                    )

        except httpx.RequestError as e:
            result["attempts"] = attempt + 1
            result["last_error"] = str(e)
            last_response_body = None
            logger.warning(
                f"Webhook 请求异常 (尝试 {attempt + 1}/{max_retries}): "
                f"{e}, url={webhook_url}"
            )

        # 重试前等待（指数退避）
        if attempt < max_retries - 1:
            delay = get_webhook_retry_delay(attempt)
            logger.info(f"等待 {delay}s 后重试...")
            # 同步延迟（生产环境用 Celery 异步任务）
            import time
            time.sleep(delay)

    logger.error(
        f"Webhook 推送最终失败: url={webhook_url}, order_id={order_id}, "
        f"attempts={result['attempts']}, error={result['last_error']}"
    )

    # 写入失败日志
    if db:
        log_record = WebhookLog(
            agent_id=agent_id,
            event_type=event_type,
            order_id=_parse_uuid(order_id),
            webhook_url=webhook_url,
            payload=payload,
            status="failed",
            attempts=result["attempts"],
            last_error=result["last_error"],
            idempotency_key=idempotency_key,
            response_code=result["last_status"] if result["last_status"] else None,
            response_body=last_response_body,
        )
        db.add(log_record)
        await db.flush()
        await db.refresh(log_record)
        result["log_id"] = str(log_record.id)

    return result


def _parse_uuid(order_id: str) -> Optional[UUID]:
    """尝试将 order_id 字符串解析为 UUID"""
    try:
        return UUID(order_id)
    except (ValueError, AttributeError):
        return None


async def push_order_update_to_agent(
    webhook_url: str,
    order_id: str,
    new_status: str,
    agent_id: UUID,
    db: Optional[AsyncSession] = None,
) -> dict:
    """推送订单状态变更给 Agent

    Args:
        webhook_url: Agent 的回调地址
        order_id: 订单 ID
        new_status: 新状态
        agent_id: Agent 用户 ID
        db: 数据库会话（可选，用于写入推送日志）

    Returns:
        推送结果
    """
    payload = {
        "event": "order.status_changed",
        "order_id": order_id,
        "status": new_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return await push_demand_to_agent(
        webhook_url=webhook_url,
        payload=payload,
        order_id=order_id,
        agent_id=agent_id,
        event_type="order_status_changed",
        db=db,
    )
