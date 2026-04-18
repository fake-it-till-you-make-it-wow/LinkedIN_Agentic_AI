"""SQLAlchemy database helpers."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import get_settings


class Base(DeclarativeBase):
    """Base declarative model."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_configured_url: str | None = None


def _sqlite_connect_args(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def configure_database(database_url: str | None = None) -> None:
    """Configure the engine and session factory for the active database URL."""

    global _configured_url, _engine, _session_factory

    resolved_url = database_url or get_settings().database_url
    if (
        _configured_url == resolved_url
        and _engine is not None
        and _session_factory is not None
    ):
        return

    _engine = create_engine(
        resolved_url,
        future=True,
        pool_pre_ping=True,
        connect_args=_sqlite_connect_args(resolved_url),
    )

    if resolved_url.startswith("sqlite"):

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    _session_factory = sessionmaker(
        bind=_engine, autoflush=False, autocommit=False, future=True
    )
    _configured_url = resolved_url


def get_engine() -> Engine:
    """Return the configured SQLAlchemy engine."""

    configure_database()
    assert _engine is not None
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the configured SQLAlchemy session factory."""

    configure_database()
    assert _session_factory is not None
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency returning a database session."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_database() -> None:
    """Create all tables for local development and tests."""

    Base.metadata.create_all(bind=get_engine())


def healthcheck_query() -> None:
    """Execute a trivial SQL statement to ensure connectivity."""

    with get_session_factory()() as session:
        session.execute(text("SELECT 1"))
