"""SQLAlchemy engine/session + declarative base."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    return create_engine(database_url, future=True)


def make_session_factory(database_url: str):
    return sessionmaker(bind=make_engine(database_url), future=True, expire_on_commit=False)


def init_db(database_url: str) -> None:
    """Create all tables (dev/test convenience; Alembic owns prod migrations)."""
    from . import models  # noqa: F401  (ensure models are imported/registered)

    Base.metadata.create_all(make_engine(database_url))
