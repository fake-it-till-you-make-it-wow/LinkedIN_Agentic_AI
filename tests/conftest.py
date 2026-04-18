"""Shared pytest fixtures."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def database_url(monkeypatch: pytest.MonkeyPatch) -> str:
    """Configure an isolated SQLite database per test."""

    base_dir = Path("tests/test_dbs")
    base_dir.mkdir(parents=True, exist_ok=True)
    db_path = base_dir / f"{uuid.uuid4()}.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)

    from backend.app.config import get_settings

    get_settings.cache_clear()
    return url


@pytest.fixture()
def app_client(database_url: str) -> TestClient:
    """Return a test client bound to the isolated database."""

    from backend.app.database import configure_database, init_database
    from backend.app.main import create_app

    configure_database(database_url)
    init_database()

    with TestClient(create_app()) as client:
        yield client


@pytest.fixture()
def db_session(database_url: str):
    """Return a raw SQLAlchemy session for service tests."""

    from backend.app.database import (
        configure_database,
        get_session_factory,
        init_database,
    )

    configure_database(database_url)
    init_database()
    with get_session_factory()() as session:
        yield session
