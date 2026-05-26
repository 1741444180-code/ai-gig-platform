"""SQLAlchemy async database engine."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    getattr(settings, 'database_url', settings.DATABASE_URL),
    echo=getattr(settings, 'debug', False),
    pool_size=getattr(settings, 'db_pool_size', settings.DB_POOL_SIZE),
    max_overflow=getattr(settings, 'db_max_overflow', settings.DB_MAX_OVERFLOW),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    """FastAPI dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
