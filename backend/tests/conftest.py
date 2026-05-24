"""Shared test fixtures for A00062 backend tests."""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.engine import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.demand import Demand
from app.models.order import Order
from app.core.security import create_access_token

TEST_DATABASE_URL = "postgresql+asyncpg:///ai_gig_test"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Ensure consistent event loop policy."""
    import sys
    if sys.platform == "darwin":
        import asyncio
        policy = asyncio.DefaultEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
    yield


@pytest_asyncio.fixture(scope="function")
async def async_db():
    """Fresh database session per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(async_db: AsyncSession) -> User:
    user = User(
        id=f"user-test-{uuid.uuid4().hex[:8]}",
        phone=f"138{uuid.uuid4().hex[:8]}",
        nickname="test_user",
        role="user",
        status="active",
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(async_db: AsyncSession) -> User:
    admin = User(
        id=f"admin-test-{uuid.uuid4().hex[:8]}",
        phone=f"139{uuid.uuid4().hex[:8]}",
        nickname="test_admin",
        role="admin",
        status="active",
    )
    async_db.add(admin)
    await async_db.commit()
    await async_db.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def test_agent(async_db: AsyncSession, test_user: User) -> Agent:
    agent = Agent(
        id=f"agent-test-{uuid.uuid4().hex[:8]}",
        user_id=test_user.id,
        name=f"test_agent_{uuid.uuid4().hex[:8]}",
        description="Test agent",
        api_url="https://example.com",
        capabilities=json.dumps(["文案"], ensure_ascii=False),
        credit_score=100,
        status="active",
        is_owner_agent=False,
        max_concurrent=3,
        eta_hours=24,
    )
    async_db.add(agent)
    await async_db.commit()
    await async_db.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def client(async_db: AsyncSession):
    """HTTP client with test database override."""
    async def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
