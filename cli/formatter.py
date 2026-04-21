"""Output formatting helpers."""

from __future__ import annotations

import json
import sys
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli.config import Settings


def resolve_format(settings: Settings) -> str:
    """Resolve the effective output format."""

    if settings.quiet:
        return "json"
    if settings.format == "rich" and not sys.stdout.isatty():
        return "json"
    return settings.format


def render_output(data: Any, settings: Settings) -> None:
    """Render response data to stdout."""

    format_name = resolve_format(settings)
    if format_name == "json":
        text = json.dumps(
            data, ensure_ascii=False, separators=(",", ":") if settings.quiet else None
        )
        print(text)
        return
    if format_name == "yaml":
        print(yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip())
        return
    if format_name == "raw":
        if isinstance(data, (dict, list)):
            print(json.dumps(data, ensure_ascii=False))
        else:
            sys.stdout.write(str(data))
        return
    _render_rich(data, settings)


def _render_rich(data: Any, settings: Settings) -> None:
    console = Console(no_color=settings.no_color)
    if isinstance(data, list):
        if not data:
            console.print("(empty)")
            return
        if all(isinstance(row, dict) for row in data):
            console.print(_table_from_rows(data))
            return
        console.print(Panel(str(data), title="List"))
        return
    if isinstance(data, dict):
        console.print(_panel_from_dict(data))
        return
    console.print(str(data))


def _table_from_rows(rows: list[dict[str, Any]]) -> Table:
    table = Table()
    columns = list(rows[0].keys())[:8]
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*(str(row.get(column, "")) for column in columns))
    return table


def _panel_from_dict(data: dict[str, Any]) -> Panel:
    table = Table(show_header=False, box=None)
    table.add_column("key")
    table.add_column("value")
    for key, value in data.items():
        rendered = (
            json.dumps(value, ensure_ascii=False)
            if isinstance(value, (dict, list))
            else str(value)
        )
        table.add_row(str(key), rendered)
    return Panel(table)
