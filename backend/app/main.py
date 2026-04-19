"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.config import get_settings
from backend.app.database import configure_database, healthcheck_query, init_database
from backend.app.routers.admin import router as admin_router
from backend.app.routers.agents import router as agents_router
from backend.app.routers.github import router as github_router
from backend.app.routers.publishers import router as publishers_router
from backend.app.routers.threads import router as threads_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize local database state on startup."""

    configure_database()
    init_database()
    healthcheck_query()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(admin_router)
    app.include_router(agents_router)
    app.include_router(github_router)
    app.include_router(publishers_router)
    app.include_router(threads_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
