"""Configuration loading for the Ocean CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

FormatName = Literal["rich", "json", "yaml", "raw"]


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration."""

    base_url: str
    caller_agent_id: str | None
    spec_override: str | None
    refresh_spec: bool
    offline: bool
    timeout_seconds: float
    cache_dir: Path
    format: FormatName
    quiet: bool
    verbose: bool
    no_color: bool
    dry_run: bool


def default_cache_dir() -> Path:
    """Return the cache directory path."""

    cache_home = os.getenv("XDG_CACHE_HOME")
    if cache_home:
        return Path(cache_home) / "ocean-cli"
    return Path.home() / ".cache" / "ocean-cli"


def normalize_base_url(base_url: str) -> str:
    """Normalize base URL for httpx."""

    return base_url.rstrip("/")


def is_url(value: str) -> bool:
    """Return True when value looks like a URL."""

    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_settings(cli_overrides: dict[str, object]) -> Settings:
    """Load settings from env and explicit overrides."""

    base_url = str(
        cli_overrides.get("base_url")
        or os.getenv("OCEAN_API_BASE")
        or "http://127.0.0.1:8000"
    )
    format_name = str(cli_overrides.get("format") or "rich")
    return Settings(
        base_url=normalize_base_url(base_url),
        caller_agent_id=_optional_str(
            cli_overrides.get("caller_agent_id") or os.getenv("OCEAN_CALLER_AGENT_ID")
        ),
        spec_override=_optional_str(cli_overrides.get("spec_override")),
        refresh_spec=bool(cli_overrides.get("refresh_spec", False)),
        offline=bool(cli_overrides.get("offline", False)),
        timeout_seconds=float(cli_overrides.get("timeout_seconds", 30.0)),
        cache_dir=Path(cli_overrides.get("cache_dir") or default_cache_dir()),
        format=format_name
        if format_name in {"rich", "json", "yaml", "raw"}
        else "rich",
        quiet=bool(cli_overrides.get("quiet", False)),
        verbose=bool(cli_overrides.get("verbose", False)),
        no_color=bool(cli_overrides.get("no_color", False) or os.getenv("NO_COLOR")),
        dry_run=bool(cli_overrides.get("dry_run", False)),
    )


def _optional_str(value: object) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
