"""Spec loader tests."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from cli.config import load_settings
from cli.errors import SpecUnavailable
from cli.spec_loader import SpecLoader


def test_loads_spec_from_override_file(mini_openapi_path: Path, tmp_path: Path) -> None:
    settings = load_settings(
        {"spec_override": str(mini_openapi_path), "cache_dir": tmp_path / "cache"}
    )
    loader = SpecLoader(settings, httpx.Client())
    loaded = loader.load()
    assert loaded.source.kind == "override"
    assert "/healthz" in loaded.spec["paths"]


def test_offline_without_cache_raises(tmp_path: Path) -> None:
    settings = load_settings({"offline": True, "cache_dir": tmp_path / "cache"})
    loader = SpecLoader(settings, httpx.Client())
    with pytest.raises(SpecUnavailable):
        loader.load()


def test_corrupt_cache_raises(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "openapi.json").write_text("{bad json", encoding="utf-8")
    (cache_dir / "openapi.meta.json").write_text(
        json.dumps(
            {
                "fetched_at": "2099-01-01T00:00:00+00:00",
                "base_url": "http://127.0.0.1:8000",
            }
        ),
        encoding="utf-8",
    )
    settings = load_settings({"cache_dir": cache_dir})
    loader = SpecLoader(settings, httpx.Client())
    with pytest.raises(SpecUnavailable):
        loader.load()
