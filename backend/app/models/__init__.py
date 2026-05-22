"""SQLAlchemy ORM Models."""

# All models are defined in models.py — unified single source of truth.
from app.models.models import (
    BaseModel,
    User,
    AgentProfile,
    AgentApiKey,
    Requirement,
    RequirementMatch,
    Order,
    Payment,
    Review,
    CreditRecord,
    WebhookLog,
)


def init_db():
    """Create all tables (sync, for startup)."""
    from sqlalchemy import create_engine
    from app.config import settings
    from app.db.database import Base  # noqa

    engine_sync = create_engine(settings.database_url_sync, echo=False)
    Base.metadata.create_all(engine_sync)
