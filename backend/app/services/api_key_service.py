"""Agent API Key 管理 — 生成、验证、SHA-256 存储、Scope 权限、沙箱环境"""

import hashlib
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


# ==================== API Key 生成 ====================

def generate_api_key() -> tuple[str, str, str]:
    """生成 API Key

    格式: ak_{16位标识}_{32位随机字符}
    示例: ak_a3f1b2c4d5e6f789_xK7mN2pQ9rS4tV8wY1zB3cD5eF7gH0jL

    Returns:
        (完整Key, key_prefix, key_hash)
        - 完整Key: 返回给前端（仅创建时显示一次）
        - key_prefix: 前8位，用于用户识别
        - key_hash: SHA-256 哈希值，存储到数据库
    """
    # 16位标识（UUID 前16位 hex）
    import uuid
    uid = uuid.uuid4().hex[:16]

    # 32位随机字符（大小写字母+数字）
    charset = string.ascii_letters + string.digits
    secret = "".join(secrets.choice(charset) for _ in range(32))

    full_key = f"ak_{uid}_{secret}"
    key_prefix = full_key[:8]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, key_prefix, key_hash


def hash_api_key(key: str) -> str:
    """对 API Key 做 SHA-256 哈希（用于查询时比对）"""
    return hashlib.sha256(key.encode()).hexdigest()


# ==================== 权限验证 ====================

VALID_SCOPES = {"full", "read", "sandbox", "sandbox_test"}

SCOPE_PERMISSIONS = {
    "full": {
        "accept_order": True,
        "submit_delivery": True,
        "query_order": True,
        "query_income": True,
        "update_profile": True,
        "webhook_receive": True,
    },
    "read": {
        "accept_order": False,
        "submit_delivery": False,
        "query_order": True,
        "query_income": True,
        "update_profile": False,
        "webhook_receive": False,
    },
    "sandbox": {
        "accept_order": True,
        "submit_delivery": True,
        "query_order": True,
        "query_income": False,
        "update_profile": False,
        "webhook_receive": False,
    },
    "sandbox_test": {
        "accept_order": True,
        "submit_delivery": True,
        "query_order": True,
        "query_income": False,
        "update_profile": False,
        "webhook_receive": False,
    },
}


def check_scope_permission(scope: str, action: str) -> bool:
    """检查某个 Scope 是否有指定操作的权限"""
    perms = SCOPE_PERMISSIONS.get(scope, {})
    return perms.get(action, False)


# ==================== Webhook 重试配置 ====================

WEBHOOK_RETRY_CONFIG = {
    "max_retries": 5,
    "initial_delay_seconds": 2,
    "backoff_multiplier": 2,  # 每次延迟翻倍: 2s → 4s → 8s → 16s → 32s
    "timeout_seconds": 10,
}


def get_webhook_retry_delay(attempt: int) -> int:
    """计算第 N 次重试的延迟时间（秒）"""
    cfg = WEBHOOK_RETRY_CONFIG
    delay = cfg["initial_delay_seconds"] * (cfg["backoff_multiplier"] ** attempt)
    return int(min(delay, 60))  # 最大60秒


def get_webhook_idempotency_key(webhook_url: str, order_id: str, attempt: int) -> str:
    """生成 Webhook 幂等性 Key

    同一 URL + 订单 + 重试次数 的组合保证唯一，
    防止重复推送导致 Agent 重复处理。
    """
    raw = f"{webhook_url}:{order_id}:{attempt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
