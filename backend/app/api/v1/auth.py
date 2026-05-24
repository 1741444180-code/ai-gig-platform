"""Auth API — 登录/验证码/Token刷新/登出 (auth-04/05/06/07)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.services.sms_service import send_sms_code, verify_sms_code
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


# ── Request Schemas ──────────────────────────────────────────────

class SendCodeRequest(BaseModel):
    phone: str


class SendCodeResponse(BaseModel):
    success: bool
    message: str
    code: str | None = None  # 仅开发模式返回


class LoginRequest(BaseModel):
    phone: str
    sms_code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: str
    phone: str
    nickname: str | None
    avatar_url: str | None
    role: str

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/send-code", response_model=SendCodeResponse)
async def send_code(
    req: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """发送短信验证码 (auth-04).

    接收手机号 → 生成6位验证码 → 存储(含过期) → 开发模式打印日志 → 返回结果。
    """
    result = await send_sms_code(req.phone, db)
    return result


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机号+验证码登录 (auth-05).

    接收phone+sms_code → 验证 → 新用户自动注册 → 返回JWT Token + 用户信息。
    """
    # 验证验证码
    user = await verify_sms_code(req.phone, req.sms_code, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="验证码错误或已过期",
        )

    # 更新最后登录时间
    from datetime import datetime, timedelta, timezone
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(user)

    # 生成 Token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserInfo(
            id=user.id,
            phone=user.phone,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            role=user.role,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """刷新 Access Token (auth-06).

    接收refresh_token → 验证 → 返回新access_token + 用户信息。
    """
    payload = decode_token(req.refresh_token)

    # 验证是refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 生成新 Token
    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserInfo(
            id=user.id,
            phone=user.phone,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            role=user.role,
        ),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户信息。

    需要 JWT Bearer Token 认证。
    """
    return UserInfo(
        id=current_user.id,
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
    )
