"""Runtime configuration helpers."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AgentLinkedIn"
    database_url: str = "sqlite:///./agentlinkedin.db"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8100
    mcp_server_url: str = "http://127.0.0.1:8100/sse"
    pm_agent_id: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
