"""Shared test fixtures for A00062 backend tests.

pytest fixtures:
- async_db           : per-function async DB session (PostgreSQL test DB)
- test_client        : AsyncClient with DB override
- test_user          : persisted User
- test_admin         : persisted admin User
- test_agent         : persisted Agent with valid API key
- user_token         : authenticated user access_token
- user_token_headers : Authorization headers for user_token
- admin_token        : admin access_token
- agent_key_headers  : Authorization headers for agent API key
"""

import asyncio
import json
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.db.engine import get_db
from app.models.user import User
from app.models.agent import Agent
from app.core.security import create_access_token, token_blacklist
from app.services.agent_key_service import generate_api_key

# ── PostgreSQL test DB ─────────────────────────────────────────────
TEST_DATABASE_URL = "postgresql+asyncpg://lijianquan@localhost:5432/ai_gig_test"


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_db():
    """Per-function async DB session against ai_gig_test PG database.

    Uses the existing test DB (created manually) so schema migrations
    don't need to run during tests. The DB should already contain all
    tables from the main schema.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Clear token blacklist between tests
    token_blacklist.clear()

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_client(async_db):
    """AsyncClient with test DB dependency override."""
    async def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(async_db) -> User:
    """Persisted test user (random phone)."""
    user = User(
        id=f"user-{uuid.uuid4().hex[:8]}",
        phone=f"138{uuid.uuid4().hex[:8]}",
        nickname="test_user",
        role="user",
        status="active",
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_admin(async_db) -> User:
    """Persisted admin user."""
    admin = User(
        id=f"admin-{uuid.uuid4().hex[:8]}",
        phone=f"139{uuid.uuid4().hex[:8]}",
        nickname="test_admin",
        role="admin",
        status="active",
    )
    async_db.add(admin)
    await async_db.commit()
    await async_db.refresh(admin)
    return admin


@pytest_asyncio.fixture(scope="function")
async def test_agent(async_db, test_user) -> Agent:
    """Persisted test agent with valid API key hash stored in DB."""
    plain_key, key_hash = generate_api_key()
    agent = Agent(
        id=f"agent-{uuid.uuid4().hex[:8]}",
        user_id=test_user.id,
        name=f"test_agent_{uuid.uuid4().hex[:8]}",
        description="Test agent for unit tests",
        api_url="https://example.com/agent",
        capabilities=json.dumps(["文案", "图片"], ensure_ascii=False),
        mode="auto",
        api_key_hash=key_hash,
        api_key_count=1,
        credit_score=100,
        status="active",
        is_owner_agent=False,
        max_concurrent=3,
        eta_hours=24,
    )
    async_db.add(agent)
    await async_db.commit()
    await async_db.refresh(agent)
    # Store plain key on the object so tests can retrieve it
    agent._plain_api_key = plain_key
    return agent


@pytest_asyncio.fixture(scope="function")
async def user_token(test_client, test_user) -> str:
    """Send SMS code + login → return access_token."""
    phone = test_user.phone
    await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
    resp = await test_client.post("/api/v1/auth/login", json={
        "phone": phone,
        "sms_code": "888888",
    })
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def user_token_headers(user_token) -> dict:
    """Authorization header dict for user token."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_token(test_client, test_admin) -> str:
    """Admin user login token."""
    phone = test_admin.phone
    await test_client.post("/api/v1/auth/send-code", json={"phone": phone})
    resp = await test_client.post("/api/v1/auth/login", json={
        "phone": phone,
        "sms_code": "888888",
    })
    assert resp.status_code == 200, f"admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def agent_key_headers(test_agent) -> dict:
    """Authorization header dict using Agent API key."""
    return {"Authorization": f"Bearer {test_agent._plain_api_key}"}