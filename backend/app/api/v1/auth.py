"""认证模块 - 微信登录、手机号登录、用户信息管理"""

import httpx
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    get_current_active_user,
)
from app.db.database import get_db
from app.models.models import User
from app.schemas.user import (
    LoginResponse,
    PhoneLoginRequest,
    SendCodeRequest,
    Token,
    UserResponse,
    UserUpdate,
    WechatLoginRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


# ==================== 微信登录 ====================

async def _wechat_code2session(code: str) -> dict:
    """调用微信code2session接口获取openid/unionid/session_key

    Args:
        code: 微信小程序/公众号登录code

    Returns:
        微信返回的session数据

    Raises:
        HTTPException: 微信接口调用失败
    """
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

    # 检查微信返回的错误码
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
    """微信登录接口

    接收微信授权code，调用微信API获取openid/unionid。
    首次登录自动创建用户账号。

    返回 access_token 和用户信息。
    """
    # 1. 调用微信code2session获取openid
    wechat_data = await _wechat_code2session(req.code)
    openid = wechat_data.get("openid")
    unionid = wechat_data.get("unionid")
    session_key = wechat_data.get("session_key")  # 注意：生产环境不要返回给前端

    if not openid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="微信登录失败，未获取到openid",
        )

    # 2. 查找或创建用户
    result = await db.execute(select(User).where(User.openid == openid))
    user = result.scalar_one_or_none()

    if user is None:
        # 首次登录，创建新用户
        user = User(openid=openid, unionid=unionid)
        db.add(user)
        await db.flush()  # 获取生成的user.id
        logger.info(f"新用户注册成功: openid={openid[:8]}***")
    else:
        # 更新unionid（如果之前没有）
        if unionid and not user.unionid:
            user.unionid = unionid

    # 3. 生成JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "openid": user.openid}
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_info=UserResponse.model_validate(user),
    )


# ==================== 手机号登录 ====================

# 测试用验证码存储（生产环境应使用Redis）
_phone_verify_codes: dict[str, str] = {}


@router.post("/phone/send_code", summary="发送手机验证码")
async def send_phone_code(req: SendCodeRequest):
    """发送手机验证码

    MVP阶段：验证码固定为"123456"用于测试。
    生产环境应接入短信服务商（如阿里云短信）。
    """
    # MVP: 固定验证码
    verify_code = "123456"
    _phone_verify_codes[req.phone] = verify_code

    # TODO: 生产环境替换为真实短信发送
    # await _send_sms(req.phone, verify_code)

    logger.info(f"发送验证码到 {req.phone}: {verify_code}")
    return {"message": "验证码已发送（MVP阶段请在控制台查看）", "test_code": verify_code}


@router.post("/phone/login", response_model=LoginResponse, summary="手机号登录")
async def phone_login(
    req: PhoneLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机号+验证码登录

    MVP阶段验证码固定为"123456"用于测试。
    首次登录自动创建用户账号。
    """
    # 1. 验证验证码
    stored_code = _phone_verify_codes.get(req.phone)
    if not stored_code or stored_code != req.verify_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    # 验证通过后删除（一次性使用）
    del _phone_verify_codes[req.phone]

    # 2. 查找或创建用户
    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(phone=req.phone)
        db.add(user)
        await db.flush()
        logger.info(f"新手机号用户注册: {req.phone}")
    else:
        logger.info(f"手机号用户登录: {req.phone}")

    # 3. 生成JWT token
    access_token = create_access_token(
        data={"sub": str(user.id), "phone": user.phone}
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_info=UserResponse.model_validate(user),
    )


# ==================== 用户信息 ====================

@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(
    current_user: User = Depends(get_current_active_user),
):
    """获取当前登录用户的个人信息

    需要Bearer token认证。
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse, summary="更新用户信息")
async def update_me(
    req: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的昵称和/或头像

    需要Bearer token认证。
    只有非空字段会被更新。
    """
    if req.nickname is not None:
        current_user.nickname = req.nickname
    if req.avatar is not None:
        current_user.avatar = req.avatar

    await db.flush()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)
