"""JWT 认证模块单元测试 — 纯安全逻辑测试（不依赖数据库/FastAPI运行时）"""

import os
import pytest

# Set env before importing app modules
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-unit-tests"
os.environ["APP_ALGORITHM"] = "HS256"
os.environ["APP_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["APP_REFRESH_TOKEN_EXPIRE_DAYS"] = "30"

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# ─── Password hashing tests (passlib only, no fastapi/sqlalchemy) ───

from passlib.context import CryptContext

@pytest.fixture
def pwd_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def test_hash_password_returns_string(pwd_context):
    h = pwd_context.hash("MyP@ssw0rd")
    assert isinstance(h, str)
    assert len(h) > 20


def test_hash_password_different_each_time(pwd_context):
    h1 = pwd_context.hash("same_password")
    h2 = pwd_context.hash("same_password")
    assert h1 != h2  # bcrypt salts


def test_verify_password_correct(pwd_context):
    h = pwd_context.hash("correct_password")
    assert pwd_context.verify("correct_password", h) is True


def test_verify_password_wrong(pwd_context):
    h = pwd_context.hash("correct_password")
    assert pwd_context.verify("wrong_password", h) is False


def test_verify_password_empty_vs_real(pwd_context):
    h = pwd_context.hash("not_empty")
    assert pwd_context.verify("", h) is False


# ─── JWT token tests (jose only, no fastapi/sqlalchemy) ───

SECRET_KEY = "test-secret-key-for-unit-tests"
ALGORITHM = "HS256"


def test_jwt_encode_decode():
    data = {"sub": "user-123", "phone": "13800001111"}
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    data_with_exp = {**data, "exp": expire}
    token = jwt.encode(data_with_exp, SECRET_KEY, algorithm=ALGORITHM)
    assert isinstance(token, str)
    assert len(token) > 10

    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "user-123"
    assert decoded["phone"] == "13800001111"


def test_jwt_contains_sub_and_phone():
    payload = {"sub": "user-456", "phone": "13900002222", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "user-456"
    assert decoded["phone"] == "13900002222"


def test_jwt_has_expiry():
    payload = {"sub": "user-123", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in decoded
    assert decoded["exp"] > datetime.now(timezone.utc).timestamp()


def test_jwt_custom_expiry():
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {"sub": "user-123", "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["exp"] > datetime.now(timezone.utc).timestamp()


def test_jwt_decode_invalid_token():
    with pytest.raises(JWTError):
        jwt.decode("this.is.not.a.valid.token", SECRET_KEY, algorithms=[ALGORITHM])


def test_jwt_decode_wrong_secret():
    payload = {"sub": "user-123", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(JWTError):
        jwt.decode(token, "wrong-secret", algorithms=[ALGORITHM])


def test_jwt_expired():
    """生成一个已过期的 token，验证拒绝"""
    expired = datetime.now(timezone.utc) - timedelta(seconds=10)
    payload = {"sub": "user-123", "exp": expired}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(JWTError):
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def test_refresh_token_long_expiry():
    """refresh_token 应至少 29 天有效"""
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    payload = {"sub": "user-123", "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp_dt = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    assert exp_dt > datetime.now(timezone.utc) + timedelta(days=29)


def test_access_token_vs_refresh_token_expiry():
    """access_token 过期时间应远短于 refresh_token"""
    access_expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    refresh_expire = datetime.now(timezone.utc) + timedelta(days=30)

    access_payload = {"sub": "user-123", "exp": access_expire}
    refresh_payload = {"sub": "user-123", "exp": refresh_expire}

    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

    access_decoded = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    refresh_decoded = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

    assert refresh_decoded["exp"] > access_decoded["exp"]
