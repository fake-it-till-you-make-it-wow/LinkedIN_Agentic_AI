"""Help catalog sanity checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from cli.help_catalog import CATALOG


def test_catalog_covers_all_operations() -> None:
    spec = json.loads(Path("docs/openapi.json").read_text(encoding="utf-8"))
    operation_ids = {
        operation["operationId"]
        for path_item in spec["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "delete"}
    }
    assert operation_ids <= set(CATALOG)


def test_catalog_uses_english_help() -> None:
    forbidden = re.compile(r"[가-힣ぁ-んァ-ン一-龯]")
    for entry in CATALOG.values():
        assert forbidden.search(entry.short) is None
        assert forbidden.search(entry.long) is None
        assert all(forbidden.search(example) is None for example in entry.examples)
