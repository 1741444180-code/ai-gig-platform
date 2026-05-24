"""Shared test fixtures for A00062 backend tests."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.engine import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.demand import Demand
from app.models.order import Order
from app.core.security import create_access_token

TEST_DATABASE_URL = "postgresql+asyncpg:///ai_gig_test"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield e
    await e.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db(engine):
    """Create tables once per session."""
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def async_db(engine) -> AsyncSession:
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()


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
        capabilities=["文案"],
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


def make_user_token(user_id: str) -> str:
    return create_access_token(user_id=user_id)


def make_admin_token(user_id: str) -> str:
    return create_access_token(user_id=user_id)


@pytest_asyncio.fixture
async def client(async_db: AsyncSession):
    """Override get_db dependency to use test session."""
    async def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, is_async=True)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
