"""Ocean CLI application entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import click
import httpx
from rich.console import Console
from rich.panel import Panel

from cli.binder import OperationBinder
from cli.client import ApiClient
from cli.config import Settings, load_settings
from cli.errors import OceanError
from cli.formatter import render_output
from cli.spec_loader import LoadedSpec, SpecLoader

ROOT_HELP = (
    "Talk to the AgentLinkedIn backend from your terminal.\n\n"
    "Common starting points:\n"
    "  ocean health\n"
    "  ocean agents list\n"
    "  ocean demo stream --max-events 3\n\n"
    "Run 'ocean <group> --help' to see more."
)


def main() -> None:
    """CLI entrypoint."""

    try:
        settings = load_settings(_parse_early_global_flags(sys.argv[1:]))
        loaded_spec = _load_spec(settings)
        client = ApiClient(settings)
        app = create_click_app(settings, loaded_spec, client)
        try:
            app(standalone_mode=False)
        finally:
            client.close()
    except click.UsageError as exc:
        Console(stderr=True).print(str(exc))
        raise SystemExit(5) from exc
    except click.ClickException as exc:
        exc.show()
        raise SystemExit(exc.exit_code) from exc
    except OceanError as exc:
        _print_error(exc, settings if "settings" in locals() else None)
        raise SystemExit(exc.exit_code) from exc


def _load_spec(settings: Settings) -> LoadedSpec:
    http = httpx.Client(base_url=settings.base_url, timeout=settings.timeout_seconds)
    try:
        return SpecLoader(settings, http).load()
    finally:
        http.close()


def _build_app(
    settings: Settings, loaded_spec: LoadedSpec, client: ApiClient
) -> tuple[click.Group, dict[tuple[str, ...], Any]]:
    @click.group(
        help=ROOT_HELP,
        invoke_without_command=False,
        context_settings={"help_option_names": ["--help"]},
    )
    @click.option(
        "--base-url",
        default=settings.base_url,
        show_default=True,
        help="Base backend URL.",
    )
    @click.option(
        "--spec",
        "spec_override",
        default=settings.spec_override,
        help="OpenAPI spec path or URL.",
    )
    @click.option(
        "--refresh-spec",
        is_flag=True,
        default=settings.refresh_spec,
        help="Refresh the cached spec.",
    )
    @click.option(
        "--offline",
        is_flag=True,
        default=settings.offline,
        help="Use cached spec only.",
    )
    @click.option(
        "--format",
        "format_name",
        default=settings.format,
        show_default=True,
        help="Output format.",
    )
    @click.option(
        "--as",
        "caller_agent_id",
        default=settings.caller_agent_id,
        help="Default caller agent ID.",
    )
    @click.option(
        "--timeout",
        default=settings.timeout_seconds,
        show_default=True,
        help="Request timeout in seconds.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        default=settings.dry_run,
        help="Print the equivalent curl command.",
    )
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
        default=settings.verbose,
        help="Show request details.",
    )
    @click.option(
        "--no-color",
        is_flag=True,
        default=settings.no_color,
        help="Disable color output.",
    )
    @click.option(
        "--quiet",
        "-q",
        is_flag=True,
        default=settings.quiet,
        help="Print compact JSON.",
    )
    def app(
        base_url: str,
        spec_override: str | None,
        refresh_spec: bool,
        offline: bool,
        format_name: str,
        caller_agent_id: str | None,
        timeout: float,
        dry_run: bool,
        verbose: bool,
        no_color: bool,
        quiet: bool,
    ) -> None:
        del base_url, spec_override, refresh_spec, offline, format_name
        del caller_agent_id, timeout, dry_run, verbose, no_color, quiet

    binder = OperationBinder(loaded_spec.spec)
    operation_map = binder.register(app, client)
    _register_meta_commands(app, loaded_spec, binder, operation_map, client)
    return app, operation_map


def create_click_app(
    settings: Settings, loaded_spec: LoadedSpec, client: ApiClient
) -> click.Group:
    """Create the click command tree."""

    app, _ = _build_app(settings, loaded_spec, client)
    return app


def _register_meta_commands(
    app: click.Group,
    loaded_spec: LoadedSpec,
    binder: OperationBinder,
    operation_map: dict[tuple[str, ...], Any],
    client: ApiClient,
) -> None:
    @app.command("describe")
    @click.argument("group")
    @click.argument("command")
    def describe(group: str, command: str) -> None:
        operation = operation_map[(group, command)]
        payload = {
            "method": operation.method,
            "path": operation.path,
            "operation_id": operation.operation_id,
            "parameters": [
                {
                    "name": parameter.name,
                    "in": parameter.location,
                    "required": parameter.required,
                }
                for parameter in operation.parameters
            ],
            "request_body_content_type": operation.request_body_content_type,
        }
        render_output(payload, client.settings)

    @app.command("raw")
    @click.argument("method")
    @click.argument("path")
    @click.option("--body", default=None, help="Optional JSON body.")
    def raw_request(method: str, path: str, body: str | None) -> None:
        parsed_body = json.loads(body) if body else None
        result = client.request(
            method,
            path,
            path_params={},
            query_params={},
            headers={},
            body=parsed_body,
            content_type="application/json" if parsed_body is not None else None,
        )
        render_output(result, client.settings)

    @app.group("spec", help="Inspect the current spec")
    def spec_group() -> None:
        pass

    @spec_group.command("show")
    def spec_show() -> None:
        render_output(
            {
                "source": loaded_spec.source.location,
                "kind": loaded_spec.source.kind,
                "fetched_at": loaded_spec.source.fetched_at,
                "paths": len(loaded_spec.spec.get("paths", {})),
                "operations": len(binder.operations()),
            },
            client.settings,
        )


def _parse_early_global_flags(argv: list[str]) -> dict[str, object]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--base-url")
    parser.add_argument("--spec", dest="spec_override")
    parser.add_argument("--refresh-spec", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--format")
    parser.add_argument("--as", dest="caller_agent_id")
    parser.add_argument("--timeout", dest="timeout_seconds", type=float)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    namespace, _ = parser.parse_known_args(argv)
    overrides = vars(namespace)
    return {
        key: value for key, value in overrides.items() if value not in (None, False)
    }


def _print_error(exc: OceanError, settings: Settings | None) -> None:
    console = Console(
        stderr=True, no_color=False if settings is None else settings.no_color
    )
    console.print(Panel(str(exc), title="Error"))
