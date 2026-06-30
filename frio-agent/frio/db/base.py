"""SQLAlchemy engine/session + declarative base.

Engines are cached per URL so ``init_db`` and ``make_session_factory`` share the
SAME engine for a given URL. This is required for correctness with in-memory
SQLite (``sqlite://``): two separate engines would be two isolated in-memory
databases, so tables created by ``init_db`` would be invisible to the session.
It also avoids spinning up a fresh connection pool on every DB call.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


_ENGINES: dict[str, Engine] = {}


def make_engine(database_url: str) -> Engine:
    engine = _ENGINES.get(database_url)
    if engine is None:
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            # One shared in-memory DB across all connections/threads for this URL.
            engine = create_engine(
                database_url, future=True, poolclass=StaticPool,
                connect_args={"check_same_thread": False})
        else:
            engine = create_engine(database_url, future=True)
        _ENGINES[database_url] = engine
    return engine


def make_session_factory(database_url: str):
    return sessionmaker(bind=make_engine(database_url), future=True, expire_on_commit=False)


def init_db(database_url: str) -> None:
    """Create all tables (dev/test convenience; Alembic owns prod migrations)."""
    from . import models  # noqa: F401  (ensure models are imported/registered)

    Base.metadata.create_all(make_engine(database_url))
