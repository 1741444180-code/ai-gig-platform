"""用户模块 — 注册、登录、手机绑定、微信登录（占位）、实名认证（占位）

注意：核心注册/登录逻辑已由 auth.py 提供（/api/v1/auth/*）。
本模块提供 /api/v1/users/* 端点，包括：
- 注册（复用 auth 逻辑的独立端点）
- 密码登录（复用 auth 逻辑的独立端点）
- 发送手机验证码（MVP 固定码）
- 绑定/验证手机验证码
- 微信登录（TODO 占位）
- 实名认证（TODO 占位）
"""

import re
import logging
from datetime import timedelta

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    get_current_active_user,
)
from app.db.database import get_db
from app.models.models import User
from app.schemas.user import (
    LoginResponse,
    PasswordLoginRequest,
    RegisterRequest,
    SendCodeRequest,
    UserResponse,
    WechatLoginRequest,
    TokenPair,
)

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# ─── MVP 阶段内存存储验证码 ───
_phone_verify_codes: dict[str, str] = {}

# ─── 手机号正则 ───
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


# ==================== 请求模型 ====================

class BindPhoneRequest(BaseModel):
    """绑定手机验证码请求"""
    phone: str = Field(..., description="手机号", pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., description="验证码", min_length=4, max_length=8)


class RealnameRequest(BaseModel):
    """实名认证请求"""
    real_name: str = Field(..., description="真实姓名", min_length=2, max_length=64)
    id_card: str = Field(..., description="身份证号", min_length=15, max_length=18)


# ==================== 用户注册 ====================

@router.post("/register", response_model=LoginResponse, summary="用户注册（手机号+密码）")
async def user_register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机号+密码注册

    - 验证手机号格式、密码长度≥6
    - 检查手机号是否已注册
    - bcrypt 哈希密码
    - 返回 user_id, phone, nickname, token
    """
    # 1. 检查手机号是否已注册
    result = await db.execute(select(User).where(User.phone == req.phone))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已注册",
        )

    # 2. 创建新用户
    user = User(
        phone=req.phone,
        password_hash=hash_password(req.password),
        nickname=req.nickname or f"用户{req.phone[-4:]}",
        role="user",
        phone_verified=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"新用户注册成功: phone={req.phone}, user_id={user.id}")

    # 3. 生成 token
    access_token = create_access_token(data={"sub": str(user.id), "phone": user.phone})

    return LoginResponse(
        access_token=access_token,
        refresh_token="",
        user_info=UserResponse.model_validate(user),
    )


# ==================== 用户登录 ====================

@router.post("/login", response_model=LoginResponse, summary="用户登录（手机号+密码）")
async def user_login(
    req: PasswordLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """手机号+密码登录

    - 验证手机号+密码
    - 返回 access_token, refresh_token, user_info
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

    # 3. 检查账号状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被禁用",
        )

    logger.info(f"用户登录成功: phone={req.phone}")

    # 4. 生成 token 对
    access_token = create_access_token(data={"sub": str(user.id), "phone": user.phone})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_info=UserResponse.model_validate(user),
    )


# ==================== 发送手机验证码（MVP） ====================

@router.post("/verify-phonecode", summary="发送手机验证码（开发环境）")
async def send_verify_phone_code(req: SendCodeRequest):
    """发送手机验证码

    开发环境：固定返回验证码 "123456"
    生产环境：TODO — 接入真实短信 API（如阿里云短信、腾讯云短信）
    """
    # TODO: 生产环境接入真实短信服务
    # 示例（阿里云短信）:
    #   from aliyunsdkcore.client import AcsClient
    #   from aliyunsdkcore.request import CommonRequest
    #   client = AcsClient(settings.ALIYUN_ACCESS_KEY_ID, ...)
    #   request = CommonRequest()
    #   request.set_domain('dysmsapi.aliyuncs.com')
    #   request.set_method('POST')
    #   request.set_action_name('SendSms')
    #   request.add_query_param('PhoneNumbers', req.phone)
    #   request.add_query_param('SignName', '平台名称')
    #   request.add_query_param('TemplateCode', 'SMS_XXXXX')
    #   request.add_query_param('TemplateParam', '{"code": verify_code}')
    #   response = client.do_action_with_exception(request)

    verify_code = "123456"
    _phone_verify_codes[req.phone] = verify_code

    logger.info(f"[MVP] 发送验证码到 {req.phone}: {verify_code}")

    return {
        "message": "验证码已发送（开发环境，请在控制台查看）",
        "test_code": verify_code,
    }


# ==================== 绑定/验证手机验证码 ====================

@router.post("/bind-phone", summary="绑定/验证手机验证码")
async def bind_phone(
    req: BindPhoneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """绑定手机号并验证验证码

    - 验证验证码
    - 更新 user.phone_verified = True
    - 如果用户尚未绑定手机号，同时更新 phone 字段
    """
    # 1. 验证验证码
    stored_code = _phone_verify_codes.get(req.phone)
    if not stored_code or stored_code != req.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期",
        )

    # 验证码使用后立即删除
    del _phone_verify_codes[req.phone]

    # 2. 检查手机号是否已被其他用户绑定
    result = await db.execute(
        select(User).where(User.phone == req.phone, User.id != current_user.id)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已被其他账号绑定",
        )

    # 3. 更新用户手机号和验证状态
    current_user.phone = req.phone
    current_user.phone_verified = True
    await db.flush()
    await db.refresh(current_user)

    logger.info(f"手机号绑定成功: user_id={current_user.id}, phone={req.phone}")

    return {"success": True, "message": "手机号绑定成功"}


# ==================== 微信登录（占位） ====================

@router.post("/wechat-login", summary="微信登录（待接入）")
async def wechat_login_placeholder(req: WechatLoginRequest):
    """微信登录 — 企业主体到位后接入

    TODO: 接入微信开放平台 code2session 接口
    - 使用 req.code 换取 openid/unionid
    - 查找或创建用户
    - 返回 token + user_info

    参考 auth.py 中的 wechat_login 实现。
    """
    # TODO: 企业主体资质到位后，配置 WECHAT_APP_ID 和 WECHAT_APP_SECRET
    # 然后调用微信 code2session 接口获取 openid
    # 参考 app/api/v1/auth.py 中的 _wechat_code2session 和 wechat_login
    logger.warning("微信登录功能尚未接入，等待企业主体资质")

    return {
        "status": "not_implemented",
        "message": "企业主体到位后接入",
    }


# ==================== 实名认证（占位） ====================

@router.post("/realname", summary="实名认证（待接入）")
async def realname_verify_placeholder(
    req: RealnameRequest,
    current_user: User = Depends(get_current_active_user),
):
    """实名认证 — 后天接入

    TODO: 接入第三方实名认证 API（如阿里云实名认证、腾讯云慧眼）
    - 验证姓名+身份证号
    - 哈希存储身份证号（不存明文）
    - 更新 user.real_name_verified = True
    """
    # TODO: 后端天后接入真实实名认证服务
    # 示例流程：
    #   1. 验证身份证号格式（正则 + 校验码）
    #   2. 调用第三方实名 API 验证姓名+身份证号匹配
    #   3. 验证通过后：
    #      current_user.real_name = real_name
    #      current_user.id_card_hash = sha256(id_card)
    #      current_user.real_name_verified = True
    #      await db.flush()
    #   4. 验证失败 → 返回 400
    logger.warning("实名认证功能尚未接入")

    return {
        "status": "not_implemented",
        "message": "实名认证后天后接入",
    }
