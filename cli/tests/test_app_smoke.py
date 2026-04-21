"""CLI smoke tests."""

from __future__ import annotations

import json

from click.testing import CliRunner

from cli.app import create_click_app
from cli.client import ApiClient
from cli.config import load_settings
from cli.spec_loader import LoadedSpec, SpecSource


def test_help_works_with_local_spec(mini_openapi_path) -> None:
    runner = CliRunner()
    settings = load_settings({"spec_override": str(mini_openapi_path)})
    app = create_click_app(
        settings,
        LoadedSpec(
            spec=json.loads(mini_openapi_path.read_text(encoding="utf-8")),
            source=SpecSource(kind="override", location="", fetched_at=None),
        ),
        ApiClient(settings),
    )
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "agents" in result.output
    assert "admin" in result.output
