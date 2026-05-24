"""SQLAlchemy ORM Models."""

from .user import User
from .agent import Agent
from .demand import Demand
from .order import Order
from .payment import Payment
from .review import Review
from .credit_log import CreditLog
from .withdraw import Withdraw


def init_db():
    """Create all tables (sync, for startup)."""
    from sqlalchemy import create_engine
    from app.config import settings
    from app.models.base import Base  # noqa

    engine_sync = create_engine(settings.database_url_sync, echo=False)
    Base.metadata.create_all(engine_sync)
