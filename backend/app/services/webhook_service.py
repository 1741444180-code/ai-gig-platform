"""Webhook 推送服务 — 需求推送 + 重试机制 + 幂等性

负责将新需求推送给匹配到的 Agent，支持：
- HTTP POST 推送到 Agent webhook_url
- 5 次重试，延迟递增（2s → 4s → 8s → 16s → 32s）
- 幂等性 Key 防止重复处理
- 推送结果记录到数据库（后续用 Celery 实现异步）
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

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
    max_retries: int = WEBHOOK_RETRY_CONFIG["max_retries"],
) -> dict:
    """推送需求给 Agent

    Args:
        webhook_url: Agent 的回调地址
        payload: 推送数据（需求信息）
        order_id: 订单/需求 ID（用于幂等性）
        max_retries: 最大重试次数

    Returns:
        推送结果: {success, attempts, last_status, last_error}
    """
    result = {
        "success": False,
        "attempts": 0,
        "last_status": 0,
        "last_error": None,
    }

    for attempt in range(max_retries):
        idempotency_key = get_webhook_idempotency_key(webhook_url, order_id, attempt)

        headers = {
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
            "X-Webhook-Event": "demand.pushed",
            "X-Webhook-Attempt": str(attempt + 1),
        }

        try:
            async with httpx.AsyncClient(
                timeout=WEBHOOK_RETRY_CONFIG["timeout_seconds"]
            ) as client:
                resp = await client.post(webhook_url, json=payload, headers=headers)
                result["attempts"] = attempt + 1
                result["last_status"] = resp.status_code

                if resp.status_code == 200:
                    result["success"] = True
                    logger.info(
                        f"Webhook 推送成功: url={webhook_url}, "
                        f"order_id={order_id}, attempt={attempt + 1}"
                    )
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
    return result


async def push_order_update_to_agent(
    webhook_url: str,
    order_id: str,
    new_status: str,
    agent_api_key_prefix: str,
) -> dict:
    """推送订单状态变更给 Agent

    Args:
        webhook_url: Agent 的回调地址
        order_id: 订单 ID
        new_status: 新状态
        agent_api_key_prefix: Agent API Key 前缀（用于标识）

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
        order_id=f"status_{order_id}",
    )
