"""Agent API Key 管理服务 (agent-02/03/06).

- API Key 生成：ak_ + 40位随机字符
- SHA-256 存储：数据库只存 hash，明文仅返回一次
- 验证中间件：Bearer Token → SHA-256 → 查库
- Key 管理：撤销/轮换/列表（每Agent最多3个Key）
"""

import hashlib
import secrets
import string
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.engine import get_db
from app.models.agent import Agent

# API Key 格式前缀
API_KEY_PREFIX = "ak_"
API_KEY_RANDOM_LENGTH = 40

# HTTP Bearer scheme for Agent API Key
agent_security = HTTPBearer()


def generate_api_key() -> tuple[str, str]:
    """生成 API Key 及其 SHA-256 hash.

    Returns:
        (plain_key, hash_key): 明文Key（返回给用户）和 SHA-256 hash（存入数据库）。
    """
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(API_KEY_RANDOM_LENGTH))
    plain_key = f"{API_KEY_PREFIX}{random_part}"
    hash_key = hashlib.sha256(plain_key.encode()).hexdigest()
    return plain_key, hash_key


def hash_api_key(plain_key: str) -> str:
    """对 API Key 进行 SHA-256 哈希。"""
    return hashlib.sha256(plain_key.encode()).hexdigest()


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(agent_security),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """FastAPI dependency: 从 Authorization: Bearer ak_xxx 验证 Agent API Key (agent-03).

    Usage:
        @router.post("/agents/action")
        async def agent_action(agent: Agent = Depends(get_current_agent)): ...

    验证逻辑：
        1. 提取 Bearer Token
        2. SHA-256 hash → 查 Agent.api_key_hash
        3. 检查 Agent 状态是否 active
        4. 返回 Agent 对象
    """
    token = credentials.credentials
    if not token.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key 格式",
        )

    token_hash = hash_api_key(token)
    result = await db.execute(
        select(Agent).where(Agent.api_key_hash == token_hash)
    )
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 无效",
        )

    if agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent 已被禁用",
        )

    return agent


def generate_webhook_secret() -> str:
    """生成 Webhook 签名密钥。"""
    return secrets.token_hex(32)
