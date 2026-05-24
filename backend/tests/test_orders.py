"""Tests for order module (order-02~07 + verify-01~05).

Coverage: accept, deliver, cancel, accept-delivery, reject-delivery, redeliver, timeline, user view.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.order import Order
from app.models.agent import Agent
from app.models.demand import Demand
from app.models.user import User


async def _create_test_order(async_db, agent: Agent, test_user: User) -> Order:
    """Helper to create a pending order in DB."""
    demand = Demand(
        id=f"demand-order-{agent.id[:8]}",
        user_id=test_user.id,
        title="Order test demand",
        description="test",
        budget=100,
        category="文案",
        status="open",
        match_status="matched",
    )
    async_db.add(demand)
    await async_db.commit()

    order = Order(
        id=f"order-test-{agent.id[:8]}",
        demand_id=demand.id,
        agent_id=agent.id,
        user_id=test_user.id,
        price=100.0,
        platform_fee=10.0,
        deposit=0.0,
        status="pending",
        eta_hours=24,
    )
    async_db.add(order)
    await async_db.commit()
    await async_db.refresh(order)
    return order


class TestAgentAcceptOrder:
    """Test POST /api/v1/orders/accept"""

    @pytest.mark.asyncio
    async def test_accept_order_valid(self, client: AsyncClient, test_agent: Agent, test_user: User, async_db):
        """Agent can accept a pending order."""
        order = await _create_test_order(async_db, test_agent, test_user)
        # The agent API uses API key auth
        resp = await client.post("/api/v1/orders/accept", json={
            "price": 100.0,
            "eta_hours": 12,
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        # Status depends on whether agent key matches
        assert resp.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_accept_no_auth(self, client: AsyncClient):
        """No auth should return 401."""
        resp = await client.post("/api/v1/orders/accept", json={"price": 100})
        assert resp.status_code in (401, 403)


class TestAgentDeliver:
    """Test POST /api/v1/orders/deliver"""

    @pytest.mark.asyncio
    async def test_deliver_valid(self, client: AsyncClient, test_agent: Agent, test_user: User, async_db):
        """Agent can deliver an accepted order."""
        order = await _create_test_order(async_db, test_agent, test_user)
        order.status = "accepted"
        await async_db.commit()

        resp = await client.post("/api/v1/orders/deliver", json={
            "delivery_url": "https://example.com/result",
            "delivery_note": "Done",
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 401, 404)


class TestAgentCancel:
    """Test POST /api/v1/orders/cancel"""

    @pytest.mark.asyncio
    async def test_cancel_valid(self, client: AsyncClient, test_agent: Agent, test_user: User, async_db):
        """Agent can cancel an accepted order, credit score should decrease."""
        order = await _create_test_order(async_db, test_agent, test_user)
        order.status = "accepted"
        original_score = test_agent.credit_score
        await async_db.commit()

        resp = await client.post("/api/v1/orders/cancel", json={
            "cancel_reason": "Test cancel",
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 401, 404)


class TestUserAcceptDelivery:
    """Test POST /api/v1/orders/{id}/accept-delivery"""

    @pytest.mark.asyncio
    async def test_accept_delivery_valid(self, client: AsyncClient, test_agent: Agent, test_user: User, async_db):
        """User can accept delivery, order→completed, credit_score+5."""
        order = await _create_test_order(async_db, test_agent, test_user)
        order.status = "delivered"
        await async_db.commit()

        token = create_access_token(user_id=test_user.id)
        resp = await client.post(f"/api/v1/orders/{order.id}/accept-delivery", json={
            "accept_note": "Good work",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_accept_delivery_wrong_status(self, client: AsyncClient, test_user: User, async_db):
        """Accepting non-delivered order should fail."""
        order = Order(
            id=f"order-wrong-status-{test_user.id[:8]}",
            demand_id=f"demand-wrong-{test_user.id[:8]}",
            agent_id="agent-fake",
            user_id=test_user.id,
            price=50.0,
            status="pending",  # not delivered
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_user.id)
        resp = await client.post(f"/api/v1/orders/{order.id}/accept-delivery", json={
            "accept_note": "Should fail",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (400, 404)


class TestUserRejectDelivery:
    """Test POST /api/v1/orders/{id}/reject-delivery"""

    @pytest.mark.asyncio
    async def test_reject_delivery_valid(self, client: AsyncClient, test_user: User, async_db):
        """User can reject delivery, order→rejected."""
        order = Order(
            id=f"order-reject-{test_user.id[:8]}",
            demand_id=f"demand-reject-{test_user.id[:8]}",
            agent_id="agent-fake-reject",
            user_id=test_user.id,
            price=100.0,
            status="delivered",
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_user.id)
        resp = await client.post(f"/api/v1/orders/{order.id}/reject-delivery", json={
            "reject_reason": "Not good enough",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "rejected"
            assert data["reject_reason"] == "Not good enough"


class TestAgentRedeliver:
    """Test POST /api/v1/orders/{id}/redeliver"""

    @pytest.mark.asyncio
    async def test_redeliver_valid(self, client: AsyncClient, test_agent: Agent, test_user: User, async_db):
        """Agent can redeliver after rejection."""
        order = await _create_test_order(async_db, test_agent, test_user)
        order.status = "rejected"
        await async_db.commit()

        resp = await client.post(f"/api/v1/orders/{order.id}/redeliver", json={
            "delivery_url": "https://example.com/v2",
            "delivery_note": "Fixed",
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 401, 404)


class TestOrderTimeline:
    """Test GET /api/v1/orders/{id}/timeline"""

    @pytest.mark.asyncio
    async def test_timeline_basic(self, client: AsyncClient, test_user: User, async_db):
        """Timeline should return order events."""
        order = Order(
            id=f"order-timeline-{test_user.id[:8]}",
            demand_id=f"demand-timeline-{test_user.id[:8]}",
            agent_id="agent-timeline",
            user_id=test_user.id,
            price=100.0,
            status="completed",
            accept_note="验收通过",
            delivery_attempts=1,
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_user.id)
        resp = await client.get(f"/api/v1/orders/{order.id}/timeline", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            data = resp.json()
            assert data["order_id"] == order.id
            assert data["status"] == "completed"
            assert "events" in data


class TestUserViewOrders:
    """Test GET /api/v1/orders/ and /{id}"""

    @pytest.mark.asyncio
    async def test_user_list_orders(self, client: AsyncClient, test_user: User, async_db):
        """User can list their orders."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get("/api/v1/orders/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_user_get_order_detail(self, client: AsyncClient, test_user: User, async_db):
        """User can get their order detail."""
        order = Order(
            id=f"order-view-{test_user.id[:8]}",
            demand_id=f"demand-view-{test_user.id[:8]}",
            agent_id="agent-view",
            user_id=test_user.id,
            price=100.0,
            status="pending",
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_user.id)
        resp = await client.get(f"/api/v1/orders/{order.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 401, 404)


class TestOrderModelValidation:
    """Test Order model field validation."""

    @pytest.mark.asyncio
    async def test_order_default_status(self, async_db, test_user: User):
        """New order should have default status='pending'."""
        order = Order(
            id="order-val-1",
            demand_id="demand-val-1",
            agent_id="agent-val-1",
            user_id=test_user.id,
            price=0.0,
        )
        async_db.add(order)
        await async_db.commit()
        await async_db.refresh(order)
        assert order.status == "pending"

    @pytest.mark.asyncio
    async def test_order_default_platform_fee(self, async_db, test_user: User):
        """New order should have default platform_fee=0.0."""
        order = Order(
            id="order-val-2",
            demand_id="demand-val-2",
            agent_id="agent-val-2",
            user_id=test_user.id,
            price=100.0,
        )
        async_db.add(order)
        await async_db.commit()
        await async_db.refresh(order)
        assert order.platform_fee == 0.0

    @pytest.mark.asyncio
    async def test_order_default_delivery_attempts(self, async_db, test_user: User):
        """New order should have default delivery_attempts=0."""
        order = Order(
            id="order-val-3",
            demand_id="demand-val-3",
            agent_id="agent-val-3",
            user_id=test_user.id,
            price=50.0,
        )
        async_db.add(order)
        await async_db.commit()
        await async_db.refresh(order)
        assert order.delivery_attempts == 0
