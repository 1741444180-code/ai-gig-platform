"""认证模块 — 注册、密码登录、微信登录、手机验证码登录、Token刷新、用户信息管理"""

import httpx
import logging
from typing import Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    verify_password,
    get_current_active_user,
)
from app.db.database import get_db
from app.models.models import User
from app.schemas.user import (
    LoginResponse,
    PasswordLoginRequest,
    PhoneLoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SendCodeRequest,
    TokenPair,
    UserResponse,
    UserUpdate,
    WechatLoginRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


# ==================== 注册 ====================

@router.post("/register", response_model=LoginResponse, summary="用户注册（手机号+密码）")
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机号+密码注册

    首次注册自动创建用户，返回 access_token + refresh_token + 用户信息。
    手机号已存在时返回 400。
    """
    # 1. 检查手机号是否已注册
    result = await db.execute(select(User).where(User.phone == req.phone))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已注册",
        )

    # 2. 创建新用户
    user = User(
        phone=req.phone,
        password_hash=hash_password(req.password),
        nickname=req.nickname or f"用户{req.phone[-4:]}",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"新用户注册成功: phone={req.phone}, user_id={user.id}")

    # 3. 生成 token 对
    access_token = create_access_token(data={"sub": str(user.id), "phone": user.phone})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_info=UserResponse.model_validate(user),
    )


# ==================== 密码登录 ====================

@router.post("/login", response_model=LoginResponse, summary="密码登录（手机号+密码）")
async def password_login(
    req: PasswordLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机号+密码登录

    验证手机号和密码，返回 access_token + refresh_token + 用户信息。
    """
    # 1. 查找用户
    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    # 2. 校验密码
    if not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    # 3. 检查状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )

    logger.info(f"密码登录成功: phone={req.phone}")

    # 4. 生成 token 对
    access_token = create_access_token(data={"sub": str(user.id), "phone": user.phone})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_info=UserResponse.model_validate(user),
    )


# ==================== Token 刷新 ====================

@router.post("/refresh", response_model=TokenPair, summary="刷新 access_token")
async def refresh_access_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """用 refresh_token 换取新的 access_token + refresh_token

    验证 refresh_token 有效性，签发新的 token 对。
    """
    # 1. 解析 refresh_token
    try:
        payload = decode_access_token(req.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌数据不完整",
        )

    # 2. 验证用户仍存在且活跃
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )

    # 3. 签发新 token 对
    new_access = create_access_token(data={"sub": str(user.id)})
    new_refresh = create_refresh_token(data={"sub": str(user.id)})
    expires_in = int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds())

    logger.info(f"Token刷新成功: user_id={user.id}")

    return TokenPair(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=expires_in,
    )


# ==================== 微信登录 ====================

async def _wechat_code2session(code: str) -> dict:
    """调用微信code2session接口获取openid/unionid/session_key"""
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.RequestError as e:
            logger.error(f"微信code2session请求失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="微信服务请求失败，请稍后重试",
            )

    if data.get("errcode") and data["errcode"] != 0:
        logger.warning(f"微信code2session返回错误: {data}")
        errcode = data.get("errcode", -1)
        errmsg = data.get("errmsg", "未知错误")

        if errcode == 40029:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的微信登录code，请重新授权",
            )
        elif errcode == 45011:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="接口调用过于频繁，请稍后重试",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"微信登录失败: {errmsg}",
            )

    return data


@router.post("/wechat/login", response_model=LoginResponse, summary="微信登录")
async def wechat_login(
    req: WechatLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """微信登录 — 自动创建用户"""
    wechat_data = await _wechat_code2session(req.code)
    openid = wechat_data.get("openid")
    unionid = wechat_data.get("unionid")

    if not openid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="微信登录失败，未获取到openid",
        )

    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(openid=openid, unionid=unionid)
        db.add(user)
        await db.flush()
        logger.info(f"新用户注册成功: openid={openid[:8]}***")
    else:
        if unionid and not user.unionid:
            user.unionid = unionid

    access_token = create_access_token(
        data={"sub": str(user.id), "openid": user.openid}
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_info=UserResponse.model_validate(user),
    )


# ==================== 手机验证码登录 ====================

_phone_verify_codes: dict[str, str] = {}


@router.post("/phone/send_code", summary="发送手机验证码")
async def send_phone_code(req: SendCodeRequest):
    """MVP阶段：验证码固定为'123456'"""
    verify_code = "123456"
    _phone_verify_codes[req.phone] = verify_code
    logger.info(f"发送验证码到 {req.phone}: {verify_code}")
    return {"message": "验证码已发送（MVP阶段请在控制台查看）", "test_code": verify_code}


@router.post("/phone/login", response_model=LoginResponse, summary="手机验证码登录")
async def phone_login(
    req: PhoneLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机验证码登录 — 自动创建用户"""
    stored_code = _phone_verify_codes.get(req.phone)
    if not stored_code or stored_code != req.verify_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    del _phone_verify_codes[req.phone]

    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(phone=req.phone)
        db.add(user)
        await db.flush()
        logger.info(f"新手机号用户注册: {req.phone}")
    else:
        logger.info(f"手机号用户登录: {req.phone}")

    access_token = create_access_token(
        data={"sub": str(user.id), "phone": user.phone}
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_info=UserResponse.model_validate(user),
    )


# ==================== 用户信息 ====================

@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """需要Bearer token认证"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse, summary="更新用户信息")
async def update_me(
    req: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的昵称和/或头像"""
    if req.nickname is not None:
        current_user.nickname = req.nickname
    if req.avatar is not None:
        current_user.avatar = req.avatar

    await db.flush()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)
