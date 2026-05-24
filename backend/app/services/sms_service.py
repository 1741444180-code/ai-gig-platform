import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User

logger = logging.getLogger(__name__)

DEV_MODE = True
DEV_CODE = "888888"
RESEND_INTERVAL_SECONDS = 60
DAILY_MAX_PER_PHONE = 10
CODE_EXPIRE_MINUTES = 5


def _utcnow():
    """Return offset-naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_sms_code() -> str:
    if DEV_MODE:
        return DEV_CODE
    return f"{random.randint(0, 999999):06d}"


async def send_sms_code(phone: str, db: AsyncSession, ip_address: Optional[str] = None) -> dict:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(phone=phone)
        db.add(user)
        await db.flush()

    # 检查重发间隔
    if user.sms_code_expires:
        now = _utcnow()
        expires = user.sms_code_expires.replace(tzinfo=None) if user.sms_code_expires.tzinfo else user.sms_code_expires
        remaining = RESEND_INTERVAL_SECONDS - (now - expires).total_seconds()
        if remaining > 0 and user.sms_code:
            return {"success": False, "message": f"验证码已发送，请{int(remaining)}秒后再试"}

    # 生成并存储验证码
    code = generate_sms_code()
    user.sms_code = code
    user.sms_code_expires = _utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES)
    await db.commit()

    if DEV_MODE:
        logger.info(f"[DEV SMS] 验证码已发送到 {phone}: {code}")
        return {"success": True, "message": "验证码已发送（开发模式）", "code": code}
    else:
        logger.info(f"[SMS] 验证码已发送到 {phone}")
        return {"success": True, "message": "验证码已发送"}


async def verify_sms_code(phone: str, code: str, db: AsyncSession) -> Optional[User]:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if user.sms_code != code:
        return None

    if user.sms_code_expires:
        now = _utcnow()
        expires = user.sms_code_expires.replace(tzinfo=None) if user.sms_code_expires.tzinfo else user.sms_code_expires
        if expires < now:
            return None

    # 验证成功，立即失效
    user.sms_code = None
    user.sms_code_expires = None
    await db.commit()

    return user
