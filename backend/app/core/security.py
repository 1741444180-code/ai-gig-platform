"""JWT认证与安全工具 — 密码哈希、Token生成/验证/刷新、用户认证"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_db
from app.models.models import User

settings = get_settings()

# ─── 密码哈希上下文 ───
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ─── HTTP Bearer 认证方案 ───
security = HTTPBearer()


# ==================== 密码工具 ====================

def hash_password(password: str) -> str:
    """用 bcrypt 对明文密码做哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== Token 生成 ====================

def _create_token(data: dict, expire_delta: timedelta) -> str:
    """内部：生成 JWT token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expire_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 access_token（短期）"""
    expire = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(data, expire)


def create_refresh_token(data: dict) -> str:
    """生成 refresh_token（长期）"""
    expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(data, expire)


# ==================== Token 验证 ====================

def decode_access_token(token: str) -> dict:
    """解析 JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== 用户认证依赖 ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Bearer token 获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户，检查 status==1"""
    if current_user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )
    return current_user
