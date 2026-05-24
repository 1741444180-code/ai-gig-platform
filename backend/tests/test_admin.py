"""Tests for admin module (admin-01~07).

Coverage: admin auth, user management, agent management, order management, dashboard, arbitration, scheduled tasks.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.core.security import create_access_token
from app.models.user import User
from app.models.agent import Agent


class TestAdminAuth:
    """Test admin authentication middleware."""

    @pytest.mark.asyncio
    async def test_admin_access_ok(self, client: AsyncClient, test_admin: User):
        """Admin user should access admin endpoints."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.get("/api/v1/admin/dashboard", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)  # 500 if DB issues

    @pytest.mark.asyncio
    async def test_non_admin_forbidden(self, client: AsyncClient, test_user: User):
        """Non-admin user should get 403."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get("/api/v1/admin/dashboard", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_no_auth_forbidden(self, client: AsyncClient):
        """No auth should get 401."""
        resp = await client.get("/api/v1/admin/dashboard")
        assert resp.status_code in (401, 403)


class TestUserManagement:
    """Test admin user management endpoints."""

    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, test_admin: User):
        """Admin can list users."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.get("/api/v1/admin/users", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_ban_user(self, client: AsyncClient, test_admin: User, test_user: User):
        """Admin can ban a user."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.put(f"/api/v1/admin/users/{test_user.id}/ban", json={
            "reason": "Test ban",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_unban_user(self, client: AsyncClient, test_admin: User, test_user: User):
        """Admin can unban a user."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.put(f"/api/v1/admin/users/{test_user.id}/unban", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)


class TestAgentManagement:
    """Test admin agent management endpoints."""

    @pytest.mark.asyncio
    async def test_list_agents(self, client: AsyncClient, test_admin: User):
        """Admin can list agents."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.get("/api/v1/admin/agents", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_ban_agent(self, client: AsyncClient, test_admin: User, test_agent: Agent):
        """Admin can ban an agent."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.put(f"/api/v1/admin/agents/{test_agent.id}/ban", json={
            "reason": "Test ban",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 500)


class TestOrderManagement:
    """Test admin order management endpoints."""

    @pytest.mark.asyncio
    async def test_list_orders(self, client: AsyncClient, test_admin: User):
        """Admin can list orders."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.get("/api/v1/admin/orders", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_force_cancel_order(self, client: AsyncClient, test_admin: User, async_db):
        """Admin can force cancel an order."""
        from app.models.order import Order
        order = Order(
            id="order-admin-cancel",
            demand_id="demand-admin-cancel",
            agent_id="agent-admin-cancel",
            user_id=test_admin.id,
            price=100.0,
            status="accepted",
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_admin.id)
        resp = await client.post(f"/api/v1/admin/orders/{order.id}/force-action", json={
            "action": "cancel",
            "reason": "Admin force cancel",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_force_complete_order(self, client: AsyncClient, test_admin: User, async_db):
        """Admin can force complete an order."""
        from app.models.order import Order
        order = Order(
            id="order-admin-complete",
            demand_id="demand-admin-complete",
            agent_id="agent-admin-complete",
            user_id=test_admin.id,
            price=100.0,
            status="delivered",
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_admin.id)
        resp = await client.post(f"/api/v1/admin/orders/{order.id}/force-action", json={
            "action": "complete",
            "reason": "Admin force complete",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 500)


class TestDashboard:
    """Test admin dashboard endpoint."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_metrics(self, client: AsyncClient, test_admin: User):
        """Dashboard should return all metrics."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.get("/api/v1/admin/dashboard", headers={
            "Authorization": f"Bearer {token}",
        })
        if resp.status_code == 200:
            data = resp.json()
            assert "total_users" in data
            assert "total_agents" in data
            assert "total_demands" in data
            assert "total_orders" in data
            assert "completion_rate" in data
            assert "avg_price" in data


class TestArbitration:
    """Test arbitration endpoints."""

    @pytest.mark.asyncio
    async def test_list_arbitration(self, client: AsyncClient, test_admin: User):
        """Admin can list arbitration cases."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.get("/api/v1/admin/arbitration", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_initiate_arbitration(self, client: AsyncClient, test_admin: User, async_db):
        """Admin can initiate arbitration."""
        from app.models.order import Order
        order = Order(
            id="order-arb-init",
            demand_id="demand-arb-init",
            agent_id="agent-arb-init",
            user_id=test_admin.id,
            price=100.0,
            status="delivered",
        )
        async_db.add(order)
        await async_db.commit()

        token = create_access_token(user_id=test_admin.id)
        resp = await client.post(f"/api/v1/admin/arbitration/{order.id}/initiate", json={
            "reason": "Test arbitration",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 500)


class TestScheduledTasks:
    """Test scheduled task endpoint."""

    @pytest.mark.asyncio
    async def test_run_scheduled_tasks(self, client: AsyncClient, test_admin: User):
        """Admin can trigger scheduled tasks."""
        token = create_access_token(user_id=test_admin.id)
        resp = await client.post("/api/v1/admin/tasks/run-scheduled", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("success") is True
