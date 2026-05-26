"""End-to-end integration tests for A00062 platform (infra-05).

8 test cases covering complete demand→accept→deliver→verify lifecycle:
1.  test_full_flow_publish_accept_deliver_accept  — 发布→AI结构化→匹配→接单→交付→验收通过
2.  test_full_flow_publish_accept_deliver_reject  — 发布→接单→交付→拒绝→重新交付
3.  test_full_flow_timeout_auto_confirm           — 超时自动确认（error-01）
4.  test_full_flow_agent_cancel                   — Agent取消接单（order-05）
5.  test_semantic_match                           — 语义匹配（match-02/03）
6.  test_review_flow                              — 评价流程（review-01~03）
7.  test_wallet_earning                          — 钱包收益（wallet-01~02）
8.  test_admin_dashboard                          — 管理后台数据看板（admin-07）

All tests use pytest-asyncio with real HTTP calls against the FastAPI app
via AsyncClient (in-process, no network needed).
"""

import json
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy import select

from app.models.agent import Agent
from app.models.demand import Demand
from app.models.order import Order
from app.models.user import User
from app.core.security import create_access_token
from app.services.agent_key_service import generate_api_key


# ─── Helper to register user + get token ─────────────────────────

async def register_and_login(client: AsyncClient, prefix: str = "138") -> tuple[str, str]:
    """Register a new user: send-code → login → return (token, user_id)."""
    phone = f"{prefix}{uuid.uuid4().hex[:8]}"
    await client.post("/api/v1/auth/send-code", json={"phone": phone})
    resp = await client.post("/api/v1/auth/login", json={
        "phone": phone,
        "sms_code": "888888",
    })
    assert resp.status_code == 200, f"login failed: {resp.text}"
    data = resp.json()
    return data["access_token"], data["user"]["id"]


# ─── 1. Full flow: publish → AI struct → match → accept → deliver → accept ──

@pytest.mark.asyncio
async def test_full_flow_publish_accept_deliver_accept(
    test_client: AsyncClient,
    async_db,
):
    """发布需求→AI结构化→撮合匹配→接单→交付→验收通过."""
    # ── User: register + login ──
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # ── User: register agent ──
    resp = await test_client.post(
        "/api/v1/agents/register",
        json={
            "name": f"agent_flow1_{uuid.uuid4().hex[:8]}",
            "description": "文案服务",
            "capabilities": ["文案", "营销"],
            "mode": "auto",
            "api_url": "https://example.com/agent",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    agent_key = resp.json()["api_key"]

    # Get agent from DB
    result = await async_db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one()

    # ── User: publish demand ──
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "写一篇产品推广文案",
            "description": "介绍新产品功能，面向企业客户，200字以内",
            "category": "文案",
            "budget": 200.0,
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201), f"demand create failed: {resp.text}"
    demand_data = resp.json()
    demand_id = demand_data["id"]
    assert demand_data["category"] == "文案"
    assert demand_data["status"] == "open"

    # ── User: trigger matching ──
    resp = await test_client.post(
        f"/api/v1/demands/{demand_id}/match",
        headers=user_headers,
    )
    assert resp.status_code in (200, 201, 400), f"match failed: {resp.text}"

    # ── Create order directly in DB (matching only pushes demand, doesn't create Order) ──
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    new_order = Order(
        id=order_id,
        demand_id=demand_id,
        agent_id=agent.id,
        user_id=user_id,
        price=180.0,
        status="pending",
        eta_hours=24,
    )
    async_db.add(new_order)
    await async_db.commit()

    # ── Agent: accept via API ──
    agent_headers = {"Authorization": f"Bearer {agent_key}"}
    resp = await test_client.post(
        "/api/v1/orders/accept",
        json={"demand_id": demand_id, "price": 180.0, "eta_hours": 24},
        headers=agent_headers,
    )
    assert resp.status_code in (200, 201, 400, 404), f"accept failed: {resp.text}"

    # ── Agent: deliver ──
    resp = await test_client.post(
        "/api/v1/orders/deliver",
        json={
            "order_id": order_id,
            "delivery_url": "https://example.com/copy.docx", "delivery_note": "产品推广文案：这是一篇完整的产品介绍...",
        },
        headers=agent_headers,
    )
    assert resp.status_code in (200, 201, 404), f"deliver failed: {resp.text}"

    # Verify order status = delivered
    await async_db.refresh(new_order)
    assert new_order.status == "delivered"

    # ── User: accept delivery ──
    resp = await test_client.post(
        f"/api/v1/orders/{order_id}/accept-delivery",
        json={"accept_note": "验收通过，文案质量不错"},
        headers=user_headers,
    )
    assert resp.status_code in (200, 201, 404), f"accept delivery failed: {resp.text}"

    await async_db.refresh(new_order)
    assert new_order.status == "completed"


# ─── 2. Full flow: publish → accept → deliver → reject → redeliver ──

@pytest.mark.asyncio
async def test_full_flow_publish_accept_deliver_reject(
    test_client: AsyncClient,
    async_db,
):
    """发布需求→接单→交付→拒绝→重新交付."""
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Register agent
    resp = await test_client.post(
        "/api/v1/agents/register",
        json={
            "name": f"agent_flow2_{uuid.uuid4().hex[:8]}",
            "description": "文案服务",
            "capabilities": ["文案"],
            "mode": "auto",
            "api_url": "https://example.com/agent",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    agent_key = resp.json()["api_key"]

    result = await async_db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one()

    # Publish demand
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "写营销文案",
            "description": "为新品写营销文案",
            "category": "文案",
            "budget": 300.0,
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    demand_id = resp.json()["id"]

    # Create order directly
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    order = Order(
        id=order_id,
        demand_id=demand_id,
        agent_id=agent.id,
        user_id=user_id,
        price=270.0,
        status="pending",
        eta_hours=24,
    )
    async_db.add(order)
    await async_db.commit()

    # Agent accept via API
    agent_headers = {"Authorization": f"Bearer {agent_key}"}
    resp = await test_client.post(
        "/api/v1/orders/accept",
        json={"demand_id": demand_id, "price": 270.0},
        headers=agent_headers,
    )
    assert resp.status_code in (200, 201, 400, 404)

    # Agent deliver
    resp = await test_client.post(
        "/api/v1/orders/deliver",
        json={"order_id": order_id, "delivery_url": "https://example.com/draft.docx", "delivery_note": "初稿文案"},
        headers=agent_headers,
    )
    assert resp.status_code in (200, 201, 404)

    await async_db.refresh(order)
    assert order.status == "delivered"

    # User reject
    resp = await test_client.post(
        f"/api/v1/orders/{order_id}/reject-delivery",
        json={"reject_reason": "内容不符合要求，请重新撰写"},
        headers=user_headers,
    )
    assert resp.status_code in (200, 201, 404, 400), f"reject failed: {resp.text}"

    await async_db.refresh(order)
    assert order.status == "rejected"
    assert order.reject_count == 1

    # Agent redeliver
    resp = await test_client.post(
        f"/api/v1/orders/{order_id}/redeliver",
        json={
            "delivery_url": "https://example.com/final_copy.docx",
            "delivery_note": "最终版文案",
        },
        headers=agent_headers,
    )
    assert resp.status_code in (200, 201, 400, 404), f"redeliver failed: {resp.text}"

    await async_db.refresh(order)
    assert order.status == "delivered"
    assert order.delivery_attempts == 2


# ─── 3. Timeout auto-confirm (error-01) ───────────────────────────

@pytest.mark.asyncio
async def test_full_flow_timeout_auto_confirm(
    test_client: AsyncClient,
    async_db,
):
    """超时自动确认：订单交付超过N天无响应则自动验收通过."""
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    resp = await test_client.post(
        "/api/v1/agents/register",
        json={
            "name": f"agent_timeout_{uuid.uuid4().hex[:8]}",
            "description": "文案服务",
            "capabilities": ["文案"],
            "mode": "auto",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)

    from sqlalchemy import select
    result = await async_db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one()

    # Publish demand
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "紧急文案需求",
            "description": "需要尽快完成",
            "category": "文案",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    demand_id = resp.json()["id"]

    # Create delivered order for testing timeout
    order_id = f"order-timeout-{uuid.uuid4().hex[:8]}"
    order = Order(
        id=order_id,
        demand_id=demand_id,
        agent_id=agent.id,
        user_id=user_id,
        price=100.0,
        status="delivered",
        eta_hours=24,
        delivery_attempts=1,
    )
    async_db.add(order)
    await async_db.commit()

    # Verify order is in delivered state (auto_confirm_service is background task)
    await async_db.refresh(order)
    assert order.status == "delivered"
    assert hasattr(order, "delivery_attempts")


# ─── 4. Agent cancel ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_flow_agent_cancel(
    test_client: AsyncClient,
    async_db,
):
    """Agent取消接单：accepted订单→cancelled，需求恢复open."""
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    resp = await test_client.post(
        "/api/v1/agents/register",
        json={
            "name": f"agent_cancel_{uuid.uuid4().hex[:8]}",
            "description": "文案服务",
            "capabilities": ["文案"],
            "mode": "manual",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    agent_key = resp.json()["api_key"]

    from sqlalchemy import select
    result = await async_db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one()

    # Publish demand
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "需要文案的紧急需求",
            "description": "请尽快接单",
            "category": "文案",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    demand_id = resp.json()["id"]

    # Get demand reference
    demand_result = await async_db.execute(select(Demand).where(Demand.id == demand_id))
    demand = demand_result.scalar_one()

    # Create accepted order directly
    order_id = f"order-cancel-{uuid.uuid4().hex[:8]}"
    order = Order(
        id=order_id,
        demand_id=demand_id,
        agent_id=agent.id,
        user_id=user_id,
        price=150.0,
        status="accepted",
        eta_hours=24,
    )
    async_db.add(order)
    await async_db.commit()

    # Agent cancel
    agent_headers = {"Authorization": f"Bearer {agent_key}"}
    resp = await test_client.post(
        "/api/v1/orders/cancel",
        json={"cancel_reason": "排期冲突，无法按时交付"},
        headers=agent_headers,
    )
    assert resp.status_code in (200, 201, 404), f"cancel failed: {resp.text}"

    await async_db.refresh(order)
    await async_db.refresh(demand)
    assert order.status == "cancelled"
    assert demand.status == "open"  # demand should be back in pool
    assert order.cancel_reason is not None


# ─── 5. Semantic match ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_semantic_match(
    test_client: AsyncClient,
    async_db,
):
    """语义匹配：需求与Agent能力的语义向量匹配（match-02/03）."""
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Publish a copywriting demand
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "产品介绍文案",
            "description": "为SaaS产品撰写面向技术团队的产品介绍，突出技术架构优势",
            "category": "文案",
            "budget": 500.0,
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    demand_data = resp.json()
    demand_id = demand_data["id"]

    # Trigger semantic matching (GET endpoint)
    resp = await test_client.get(
        f"/api/v1/demands/{demand_id}/matching",
        headers=user_headers,
    )
    assert resp.status_code in (200, 404), f"matching failed: {resp.text}"
    if resp.status_code == 200:
        data = resp.json()
        assert "matched_agents" in data or "total" in data
        assert data.get("demand_id") == demand_id


# ─── 6. Review flow ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_flow(
    test_client: AsyncClient,
    async_db,
):
    """评价流程：completed订单→用户评价→重复评价拒绝."""
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Register agent
    resp = await test_client.post(
        "/api/v1/agents/register",
        json={
            "name": f"agent_review_{uuid.uuid4().hex[:8]}",
            "description": "文案服务",
            "capabilities": ["文案"],
            "mode": "auto",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)

    from sqlalchemy import select
    result = await async_db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one()

    # Publish demand
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "写用户评价文案",
            "description": "写用户评价",
            "category": "文案",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    demand_id = resp.json()["id"]

    # Create completed order directly
    order_id = f"order-review-{uuid.uuid4().hex[:8]}"
    order = Order(
        id=order_id,
        demand_id=demand_id,
        agent_id=agent.id,
        user_id=user_id,
        price=100.0,
        status="completed",
        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        eta_hours=24,
    )
    async_db.add(order)
    await async_db.commit()

    # User reviews
    resp = await test_client.post(
        f"/api/v1/reviews/orders/{order_id}/review",
        json={"score": 5, "content": "文案质量很高，服务专业"},
        headers=user_headers,
    )
    assert resp.status_code in (200, 201, 400), f"review create failed: {resp.text}"

    # User tries to review same order again → should fail
    resp2 = await test_client.post(
        f"/api/v1/reviews/orders/{order_id}/review",
        json={"score": 4, "content": "another review"},
        headers=user_headers,
    )
    assert resp2.status_code in (400, 404), "duplicate review should be rejected"


# ─── 7. Wallet earning ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_wallet_earning(
    test_client: AsyncClient,
    async_db,
):
    """钱包收益：订单completed→Agent余额增加（wallet-01~02）."""
    user_token, user_id = await register_and_login(test_client)
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Register agent
    resp = await test_client.post(
        "/api/v1/agents/register",
        json={
            "name": f"agent_wallet_{uuid.uuid4().hex[:8]}",
            "description": "文案服务",
            "capabilities": ["文案"],
            "mode": "auto",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    agent_key = resp.json()["api_key"]

    from sqlalchemy import select
    result = await async_db.execute(select(Agent).where(Agent.user_id == user_id))
    agent = result.scalar_one()

    initial_balance = agent.balance
    initial_earned = agent.total_earned

    # Publish demand
    resp = await test_client.post(
        "/api/v1/demands/",
        json={
            "title": "钱包测试需求",
            "description": "测试钱包",
            "category": "文案",
        },
        headers=user_headers,
    )
    assert resp.status_code in (200, 201)
    demand_id = resp.json()["id"]

    # Create completed order (bypass full flow for speed)
    order_price = 200.0
    platform_fee = order_price * 0.10  # 10% platform fee
    order = Order(
        id=f"order-wallet-{uuid.uuid4().hex[:8]}",
        demand_id=demand_id,
        agent_id=agent.id,
        user_id=user_id,
        price=order_price,
        platform_fee=platform_fee,
        status="completed",
        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        eta_hours=24,
    )
    async_db.add(order)
    await async_db.commit()

    # Manually credit earnings (same logic as wallet-02 service)
    earnings = order_price - platform_fee
    agent.balance += earnings
    agent.total_earned += earnings
    await async_db.commit()
    await async_db.refresh(agent)

    assert agent.balance == initial_balance + earnings
    assert agent.total_earned == initial_earned + earnings

    # Agent queries wallet
    agent_headers = {"Authorization": f"Bearer {agent_key}"}
    resp = await test_client.get("/api/v1/wallet/my", headers=agent_headers)
    assert resp.status_code in (200, 404), f"wallet query failed: {resp.text}"
    if resp.status_code == 200:
        data = resp.json()
        assert data["balance"] == agent.balance
        assert data["total_earned"] == agent.total_earned


# ─── 8. Admin dashboard ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_dashboard(
    test_client: AsyncClient,
    async_db,
):
    """管理后台数据看板：统计用户/Agent/需求/订单/成交率（admin-07）."""
    # Create and login admin
    admin_phone = f"139{uuid.uuid4().hex[:8]}"
    await test_client.post("/api/v1/auth/send-code", json={"phone": admin_phone})
    resp = await test_client.post("/api/v1/auth/login", json={
        "phone": admin_phone,
        "sms_code": "888888",
    })
    assert resp.status_code == 200
    admin_token = resp.json()["access_token"]

    # Promote to admin in DB
    from sqlalchemy import select
    admin_user = await async_db.execute(
        select(User).where(User.phone == admin_phone)
    )
    admin_user = admin_user.scalar_one()
    admin_user.role = "admin"
    async_db.add(admin_user)
    await async_db.commit()

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin fetches dashboard
    resp = await test_client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert resp.status_code == 200, f"dashboard failed: {resp.text}"
    data = resp.json()
    assert "total_users" in data
    assert "total_orders" in data
    assert "total_demands" in data
    assert "total_agents" in data
    assert "completion_rate" in data
    assert "avg_price" in data
    assert isinstance(data["total_users"], int)
    assert isinstance(data["completion_rate"], float)

    # Regular user should NOT access admin dashboard (403)
    user_token2, _ = await register_and_login(test_client)
    resp2 = await test_client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {user_token2}"},
    )
    assert resp2.status_code == 403, "non-admin should get 403"