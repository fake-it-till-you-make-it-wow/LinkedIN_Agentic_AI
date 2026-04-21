"""Binder tests."""

from __future__ import annotations

import json
from pathlib import Path

from cli.binder import OperationBinder


def test_binder_maps_core_commands(mini_openapi_path: Path) -> None:
    spec = json.loads(mini_openapi_path.read_text(encoding="utf-8"))
    binder = OperationBinder(spec)
    commands = {(item.group, item.command_name) for item in binder.operations()}
    assert ("root", "health") in commands
    assert ("admin", "health") in commands
    assert ("agents", "list") in commands
