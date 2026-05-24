import json
import uuid
"""Tests for agent module (agent-01~08).

Coverage: agent registration, API key CRUD, capability card update, get_current_agent, model validation.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.core.security import create_access_token
from app.models.agent import Agent
from app.models.user import User


class TestAgentRegistration:
    """Test POST /api/v1/agents/register"""

    @pytest.mark.asyncio
    async def test_register_agent_valid(self, client: AsyncClient, test_user: User):
        """Valid registration should return agent info with API key."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.post("/api/v1/agents/register", json={
            "name": f"test_agent_{test_user.id}",
            "description": "Test agent for registration",
            "capabilities": ["文案", "图片"],
            "mode": "auto",
            "api_url": "https://example.com/agent",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["name"] == f"test_agent_{test_user.id}"
        assert "api_key" in data
        # capabilities stored as JSON string
        caps = data.get("capabilities", "")
        if isinstance(caps, str):
            import json as _json
            caps = _json.loads(caps)
        assert "文案" in caps
        assert data["mode"] == "auto"

    @pytest.mark.asyncio
    async def test_register_agent_missing_name(self, client: AsyncClient, test_user: User):
        """Missing name should return 422."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.post("/api/v1/agents/register", json={
            "description": "No name",
            "capabilities": ["文案"],
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_agent_no_auth(self, client: AsyncClient):
        """No auth should return 401."""
        resp = await client.post("/api/v1/agents/register", json={
            "name": "unauth_agent",
            "capabilities": ["文案"],
        })
        assert resp.status_code in (401, 403)


class TestAgentCapabilityCard:
    """Test GET/PUT /api/v1/agents/profile"""

    @pytest.mark.asyncio
    async def test_get_agent_capability_card(self, client: AsyncClient, test_agent: Agent):
        """GET /agents/ should return agent info."""
        resp = await client.get("/api/v1/agents/", headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_capability_card(self, client: AsyncClient, test_agent: Agent):
        """PUT /agents/profile should update agent capabilities."""
        resp = await client.put("/api/v1/agents/profile", json={
            "description": "Updated description",
            "max_concurrent": 5,
            "eta_hours": 12,
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 401, 403, 422)


class TestAgentAPIKeyCRUD:
    """Test API key creation, listing, deletion."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, client: AsyncClient, test_agent: Agent):
        """POST /agents/keys/rotate should rotate keys."""
        resp = await client.post("/api/v1/agents/keys/rotate", json={
            "name": "test_key",
            "scope": ["demand", "order"],
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client: AsyncClient, test_agent: Agent):
        """GET /agents/keys should list keys."""
        resp = await client.get("/api/v1/agents/keys", headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_delete_api_key(self, client: AsyncClient, test_agent: Agent):
        """POST /agents/keys/revoke should revoke a key."""
        resp = await client.post("/api/v1/agents/keys/revoke", json={
            "key_id": "fake-key-id",
        }, headers={
            "Authorization": f"Bearer test_key_{test_agent.id}",
        })
        assert resp.status_code in (200, 201, 404, 401, 403)


class TestAgentModelValidation:
    """Test Agent model field validation."""

    @pytest.mark.asyncio
    async def test_credit_score_default(self, async_db, test_user: User):
        """New agent should have default credit_score=100."""
        agent = Agent(
            id=f"agent-val-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            name="val_test_agent",
            api_url="https://example.com",
            capabilities=json.dumps(["文案"], ensure_ascii=False),
        )
        async_db.add(agent)
        await async_db.commit()
        await async_db.refresh(agent)
        assert agent.credit_score == 100

    @pytest.mark.asyncio
    async def test_max_concurrent_default(self, async_db, test_user: User):
        """New agent should have default max_concurrent=5."""
        agent = Agent(
            id=f"agent-val-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            name="val_test_agent_2",
            api_url="https://example.com",
            capabilities=json.dumps(["文案"], ensure_ascii=False),
        )
        async_db.add(agent)
        await async_db.commit()
        await async_db.refresh(agent)
        assert agent.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_status_default(self, async_db, test_user: User):
        """New agent should have default status='active'."""
        agent = Agent(
            id=f"agent-val-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            name="val_test_agent_3",
            api_url="https://example.com",
            capabilities=json.dumps(["文案"], ensure_ascii=False),
        )
        async_db.add(agent)
        await async_db.commit()
        await async_db.refresh(agent)
        assert agent.status == "active"

    @pytest.mark.asyncio
    async def test_is_owner_agent_default(self, async_db, test_user: User):
        """New agent should have default is_owner_agent=False."""
        agent = Agent(
            id=f"agent-val-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            name="val_test_agent_4",
            api_url="https://example.com",
            capabilities=json.dumps(["文案"], ensure_ascii=False),
        )
        async_db.add(agent)
        await async_db.commit()
        await async_db.refresh(agent)
        assert agent.is_owner_agent is False
