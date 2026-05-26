"""Tests for auth module: JWT auth + SMS login + token lifecycle.

8 test cases (infra-03):
1.  test_send_code_success            — 发送验证码成功
2.  test_login_success               — 登录成功获取token
3.  test_login_invalid_code          — 错误验证码拒绝登录
4.  test_token_verify_success        — token验证成功（decode验证）
5.  test_token_expired               — 过期token返回401
6.  test_token_refresh               — 刷新token获取新access_token
7.  test_logout                      — 登出后token黑名单验证
8.  test_unauthorized_access         — 未认证访问返回401
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

from app.core.security import create_access_token, create_refresh_token, decode_token, token_blacklist
from app.models.user import User


class TestSendCode:
    """Test POST /api/v1/auth/send-code"""

    @pytest.mark.asyncio
    async def test_send_code_success(self, test_client: AsyncClient):
        """发送验证码成功（开发模式返回code=888888）."""
        phone = f"138{uuid.uuid4().hex[:8]}"
        resp = await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # 开发模式下 code 字段为 "888888"
        assert data.get("code") == "888888"


class TestLogin:
    """Test POST /api/v1/auth/login"""

    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient):
        """登录成功返回 access_token + refresh_token + user 信息."""
        phone = f"138{uuid.uuid4().hex[:8]}"
        # 先获取验证码
        await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
        # 用正确验证码登录
        resp = await test_client.post("/api/v1/auth/login", json={
            "phone": phone,
            "sms_code": "888888",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        user = data["user"]
        assert user["phone"] == phone
        assert user["role"] == "user"

    @pytest.mark.asyncio
    async def test_login_invalid_code(self, test_client: AsyncClient):
        """错误验证码返回401/400，拒绝登录."""
        phone = f"138{uuid.uuid4().hex[:8]}"
        await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
        resp = await test_client.post("/api/v1/auth/login", json={
            "phone": phone,
            "sms_code": "000000",  # wrong code
        })
        assert resp.status_code in (400, 401)


class TestTokenVerify:
    """Test JWT token encode/decode/roundtrip."""

    def test_token_verify_success(self):
        """用 create_access_token 创建的 token 可被 decode 正确解析."""
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        token = create_access_token(user_id=user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "jti" in payload

    def test_token_expired(self):
        """已过期的token（exp设为过去时间）被 decode 时返回401."""
        from fastapi import HTTPException

        user_id = f"user-{uuid.uuid4().hex[:8]}"
        # 创建一个已过期1秒的token
        expired_token = create_access_token(
            user_id=user_id,
            expires_delta=timedelta(seconds=-1),
        )
        # decode时应该抛出 HTTPException 401
        try:
            decode_token(expired_token)
            assert False, "Expected HTTPException for expired token"
        except HTTPException as e:
            assert e.status_code == 401

    @pytest.mark.asyncio
    async def test_token_refresh(self, test_client: AsyncClient, test_user: User):
        """用 refresh_token 可获取新的 access_token."""
        phone = test_user.phone
        await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
        login_resp = await test_client.post("/api/v1/auth/login", json={
            "phone": phone,
            "sms_code": "888888",
        })
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # 使用 refresh_token 获取新 access_token
        resp = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200, f"refresh failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # 新token的 sub 应该等于用户id
        new_token = data["access_token"]
        new_payload = decode_token(new_token)
        assert new_payload["sub"] == test_user.id

    @pytest.mark.asyncio
    async def test_logout(self, test_client: AsyncClient, test_user: User):
        """登出后token被加入黑名单，再次使用返回401."""
        phone = test_user.phone
        await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
        login_resp = await test_client.post("/api/v1/auth/login", json={
            "phone": phone,
            "sms_code": "888888",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # 登出
        resp = await test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # 用同一个token访问 /auth/me 应该返回401
        me_resp = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 401, f"Expected 401, got {me_resp.status_code}"

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client: AsyncClient):
        """未提供token访问受保护接口返回401或403."""
        resp = await test_client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"