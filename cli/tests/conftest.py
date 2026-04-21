"""Fixtures for CLI tests."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest


@pytest.fixture()
def mini_openapi_path(tmp_path: Path) -> Path:
    """Write a tiny OpenAPI fixture."""

    path = tmp_path / "mini_openapi.json"
    path.write_text(
        json.dumps(
            {
                "openapi": "3.1.0",
                "paths": {
                    "/healthz": {
                        "get": {
                            "summary": "Health",
                            "operationId": "healthz_healthz_get",
                            "responses": {"200": {"description": "ok"}},
                        }
                    },
                    "/api/admin/health": {
                        "get": {
                            "tags": ["admin"],
                            "summary": "Admin Health",
                            "operationId": "admin_health_api_admin_health_get",
                            "responses": {"200": {"description": "ok"}},
                        }
                    },
                    "/api/agents": {
                        "get": {
                            "tags": ["agents"],
                            "summary": "List Agents",
                            "operationId": "list_agents_api_agents_get",
                            "responses": {"200": {"description": "ok"}},
                        }
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture(scope="session")
def live_server() -> str:  # type: ignore[return]
    """세션당 1회 uvicorn 서버를 임시 SQLite DB로 기동하고 seed 데이터를 주입한다."""
    import tempfile

    import uvicorn

    # 사용 가능한 포트 확보
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    # 임시 DB 경로
    db_file = tempfile.mktemp(suffix="_e2e.db")
    db_url = f"sqlite:///{db_file}"
    os.environ["DATABASE_URL"] = db_url

    from backend.app.config import get_settings

    get_settings.cache_clear()

    from backend.app.database import configure_database, init_database

    configure_database(db_url)
    init_database()

    from backend.seed import main as seed_main

    seed_main()

    from backend.app.main import create_app

    config = uvicorn.Config(
        create_app(), host="127.0.0.1", port=port, log_level="error"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(f"{base_url}/healthz", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)

    yield base_url  # type: ignore[misc]

    server.should_exit = True
    thread.join(timeout=5)
    try:
        os.unlink(db_file)
    except OSError:
        pass


@pytest.fixture(scope="session")
def seed_ids() -> dict[str, str]:
    """seed.py 에서 결정론적으로 생성되는 agent UUID를 반환한다."""
    ns = uuid.uuid5(uuid.NAMESPACE_URL, "agentlinkedin-phase1")
    return {
        "pm": str(uuid.uuid5(ns, "PM Youngsu")),
        "research": str(uuid.uuid5(ns, "Research Agent")),
        "code": str(uuid.uuid5(ns, "Code Agent")),
        "marketing": str(uuid.uuid5(ns, "Marketing Agent")),
        "design": str(uuid.uuid5(ns, "Design Agent")),
    }


@pytest.fixture()
def make_cli() -> Callable[[str], tuple]:
    """CLI app 팩토리. base_url 을 받아 (click_app, CliRunner) 를 반환한다."""
    from click.testing import CliRunner

    from cli.app import create_click_app
    from cli.client import ApiClient
    from cli.config import load_settings
    from cli.spec_loader import LoadedSpec, SpecSource

    spec_path = Path("docs/openapi.json")
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))

    clients: list[ApiClient] = []

    def _factory(base_url: str, extra_overrides: dict | None = None) -> tuple:
        overrides = {"base_url": base_url, "spec_override": str(spec_path)}
        if extra_overrides:
            overrides.update(extra_overrides)
        settings = load_settings(overrides)
        loaded_spec = LoadedSpec(
            spec=spec_data,
            source=SpecSource(
                kind="override", location=str(spec_path), fetched_at=None
            ),
        )
        client = ApiClient(settings)
        clients.append(client)
        app = create_click_app(settings, loaded_spec, client)
        return app, CliRunner()

    yield _factory  # type: ignore[misc]

    for client in clients:
        client.close()
