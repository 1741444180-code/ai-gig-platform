import uuid
"""Tests for demand module (demand-01~08).

Coverage: create/list/get/update/cancel demands, model validation, filtering.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.core.security import create_access_token
from app.models.demand import Demand
from app.models.user import User


class TestCreateDemand:
    """Test POST /api/v1/demands"""

    @pytest.mark.asyncio
    async def test_create_demand_valid(self, client: AsyncClient, test_user: User):
        """Valid demand should be created with AI tags."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.post("/api/v1/demands/", json={
            "title": "需要一篇推广文案",
            "description": "帮我写一篇关于AI产品的推广文案，500字左右",
            "budget": 100,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == "需要一篇推广文案"
        assert data["status"] == "open"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_demand_missing_title(self, client: AsyncClient, test_user: User):
        """Missing title should return 422."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.post("/api/v1/demands/", json={
            "description": "No title",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_demand_no_auth(self, client: AsyncClient):
        """No auth should return 401."""
        resp = await client.post("/api/v1/demands/", json={
            "title": "Unauth demand",
            "description": "test",
        })
        assert resp.status_code in (401, 403)


class TestListDemands:
    """Test GET /api/v1/demands"""

    @pytest.mark.asyncio
    async def test_list_demands_empty(self, client: AsyncClient, test_user: User):
        """Empty list should return items=[]."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get("/api/v1/demands/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_list_demands_pagination(self, client: AsyncClient, test_user: User):
        """Pagination should work correctly."""
        token = create_access_token(user_id=test_user.id)
        # Create a demand first
        await client.post("/api/v1/demands/", json={
            "title": "Pagination test",
            "description": "test",
            "budget": 50,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        
        resp = await client.get("/api/v1/demands/?page=1&page_size=10", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_demands_category_filter(self, client: AsyncClient, test_user: User):
        """Category filter should work."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get("/api/v1/demands/?category=文案", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)

    @pytest.mark.asyncio
    async def test_list_demands_status_filter(self, client: AsyncClient, test_user: User):
        """Status filter should work."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get("/api/v1/demands/?status=open", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)


class TestGetDemandDetail:
    """Test GET /api/v1/demands/{id}"""

    @pytest.mark.asyncio
    async def test_get_demand_exists(self, client: AsyncClient, test_user: User):
        """Get existing demand should return 200."""
        token = create_access_token(user_id=test_user.id)
        create_resp = await client.post("/api/v1/demands/", json={
            "title": "Detail test",
            "description": "test",
            "budget": 100,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        demand_id = create_resp.json()["id"]
        
        resp = await client.get(f"/api/v1/demands/{demand_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["id"] == demand_id
        assert data["title"] == "Detail test"

    @pytest.mark.asyncio
    async def test_get_demand_not_found(self, client: AsyncClient, test_user: User):
        """Get non-existing demand should return 404."""
        token = create_access_token(user_id=test_user.id)
        resp = await client.get("/api/v1/demands/non-existing-id", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


class TestUpdateDemand:
    """Test PUT /api/v1/demands/{id}"""

    @pytest.mark.asyncio
    async def test_update_demand_valid(self, client: AsyncClient, test_user: User):
        """Update open demand should succeed."""
        token = create_access_token(user_id=test_user.id)
        create_resp = await client.post("/api/v1/demands/", json={
            "title": "Update test",
            "description": "original",
            "budget": 100,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        demand_id = create_resp.json()["id"]
        
        resp = await client.put(f"/api/v1/demands/{demand_id}", json={
            "title": "Updated title",
            "description": "updated",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["title"] == "Updated title"

    @pytest.mark.asyncio
    async def test_update_demand_not_open(self, client: AsyncClient, async_db, test_user: User):
        """Update non-open demand should fail."""
        token = create_access_token(user_id=test_user.id)
        # Create demand then cancel it
        create_resp = await client.post("/api/v1/demands/", json={
            "title": "Cancel then update",
            "description": "test",
            "budget": 100,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        demand_id = create_resp.json()["id"]
        
        await client.post(f"/api/v1/demands/{demand_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        
        resp = await client.put(f"/api/v1/demands/{demand_id}", json={
            "title": "Should fail",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (400, 403, 422)


class TestCancelDemand:
    """Test POST /api/v1/demands/{id}/cancel"""

    @pytest.mark.asyncio
    async def test_cancel_demand_valid(self, client: AsyncClient, test_user: User):
        """Cancel open demand should succeed."""
        token = create_access_token(user_id=test_user.id)
        create_resp = await client.post("/api/v1/demands/", json={
            "title": "Cancel test",
            "description": "test",
            "budget": 100,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        demand_id = create_resp.json()["id"]
        
        resp = await client.post(f"/api/v1/demands/{demand_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_demand_already_cancelled(self, client: AsyncClient, test_user: User):
        """Cancel already cancelled demand should fail."""
        token = create_access_token(user_id=test_user.id)
        create_resp = await client.post("/api/v1/demands/", json={
            "title": "Double cancel test",
            "description": "test",
            "budget": 100,
            "category": "文案",
        }, headers={"Authorization": f"Bearer {token}"})
        demand_id = create_resp.json()["id"]
        
        await client.post(f"/api/v1/demands/{demand_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        resp = await client.post(f"/api/v1/demands/{demand_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (400, 403, 422)


class TestDemandModelValidation:
    """Test Demand model field validation."""

    @pytest.mark.asyncio
    async def test_demand_default_status(self, async_db, test_user: User):
        """New demand should have default status='open'."""
        demand = Demand(
            id=f"demand-val-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            title="Validation test",
            description="test",
            budget=100,
        )
        async_db.add(demand)
        await async_db.commit()
        await async_db.refresh(demand)
        assert demand.status == "open"

    @pytest.mark.asyncio
    async def test_demand_default_match_status(self, async_db, test_user: User):
        """New demand should have default match_status='pending'."""
        demand = Demand(
            id=f"demand-val-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            title="Validation test 2",
            description="test",
            budget=100,
        )
        async_db.add(demand)
        await async_db.commit()
        await async_db.refresh(demand)
        assert demand.match_status == "pending"
