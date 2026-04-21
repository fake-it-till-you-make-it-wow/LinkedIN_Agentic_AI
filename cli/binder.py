"""OpenAPI operation binding to click commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from cli.client import ApiClient
from cli.help_catalog import CATALOG, HelpEntry
from cli.sse import SseRenderer

_HTTP_METHODS = {"get", "post", "patch", "delete", "put"}


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """A bound OpenAPI parameter."""

    name: str
    location: str
    required: bool
    schema: dict[str, Any]

    @property
    def cli_name(self) -> str:
        return self.name.replace("_", "-")


@dataclass(frozen=True, slots=True)
class BoundOperation:
    """A bound OpenAPI operation."""

    group: str
    command_name: str
    method: str
    path: str
    operation_id: str
    summary: str
    description: str
    parameters: list[ParameterSpec]
    request_body_content_type: str | None
    request_body_schema: dict[str, Any] | None
    produces_sse: bool


class OperationBinder:
    """Bind OpenAPI operations into CLI commands."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.components = spec.get("components", {}).get("schemas", {})
        self._operations = self._collect_operations()

    def operations(self) -> list[BoundOperation]:
        """Return bound operations."""

        return list(self._operations)

    def register(
        self, app: click.Group, client: ApiClient
    ) -> dict[tuple[str, ...], BoundOperation]:
        """Register commands on the app."""

        groups: dict[str, click.Group] = {}
        mapping: dict[tuple[str, ...], BoundOperation] = {}
        root_commands: list[click.Command] = []
        for operation in self._operations:
            command = self._build_command(operation, client)
            if operation.group == "root":
                root_commands.append(command)
                mapping[(operation.command_name,)] = operation
                continue
            if operation.group not in groups:
                sub_app = click.Group(
                    name=operation.group, help=f"{operation.group} commands"
                )
                groups[operation.group] = sub_app
                app.add_command(sub_app)
            groups[operation.group].add_command(command)
            mapping[(operation.group, operation.command_name)] = operation
        for command in root_commands:
            app.add_command(command)
        return mapping

    def _collect_operations(self) -> list[BoundOperation]:
        operations: list[BoundOperation] = []
        group_name_counts: dict[str, dict[str, int]] = {}
        for path, path_item in self.spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method not in _HTTP_METHODS or not isinstance(operation, dict):
                    continue
                group = self._derive_group(path, operation)
                command_name = self._derive_command_name(path, method, operation)
                name_counts = group_name_counts.setdefault(group, {})
                if command_name in name_counts:
                    name_counts[command_name] += 1
                    command_name = f"{command_name}-{method}"
                else:
                    name_counts[command_name] = 1
                parameters = [
                    ParameterSpec(
                        name=item["name"],
                        location=item["in"],
                        required=bool(item.get("required", False)),
                        schema=self._resolve_schema(item.get("schema", {})),
                    )
                    for item in operation.get("parameters", [])
                ]
                request_body_content_type = None
                request_body_schema = None
                request_body = operation.get("requestBody")
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    if content:
                        request_body_content_type = next(iter(content))
                        request_body_schema = self._resolve_schema(
                            content[request_body_content_type].get("schema", {})
                        )
                produces_sse = "text/event-stream" in (
                    operation.get("responses", {}).get("200", {}).get("content", {})
                )
                operations.append(
                    BoundOperation(
                        group=group,
                        command_name=command_name,
                        method=method.upper(),
                        path=path,
                        operation_id=str(operation.get("operationId", "")),
                        summary=str(operation.get("summary", "")),
                        description=str(operation.get("description", "")),
                        parameters=parameters,
                        request_body_content_type=request_body_content_type,
                        request_body_schema=request_body_schema,
                        produces_sse=produces_sse,
                    )
                )
        return operations

    def _derive_group(self, path: str, operation: dict[str, Any]) -> str:
        tags = operation.get("tags") or []
        if tags:
            return str(tags[0])
        parts = [part for part in path.split("/") if part]
        return "root" if len(parts) <= 1 else parts[0]

    def _derive_command_name(
        self, path: str, method: str, operation: dict[str, Any]
    ) -> str:
        operation_id = str(operation.get("operationId", ""))
        if path == "/healthz":
            return "health"
        if operation_id == "admin_health_api_admin_health_get":
            return "health"
        if operation_id.startswith("list_"):
            return "list"
        if operation_id.startswith("create_"):
            return "create"
        if operation_id.startswith("get_"):
            if path.endswith("/stats"):
                return "stats"
            if path.endswith("/threads"):
                return "threads"
            return "get"
        if operation_id.startswith("update_"):
            return "update"
        if operation_id.startswith("search_"):
            return "search"
        if "verify" in operation_id and "unverify" not in operation_id:
            return "verify"
        if "unverify" in operation_id:
            return "unverify"
        if "upload" in operation_id:
            return "upload"
        if "download_template" in operation_id:
            return "template"
        if "webhook" in operation_id:
            return "webhook"
        if "demo_stream" in operation_id:
            return "stream"
        if method == "delete":
            return "delete"
        return operation_id.replace("_", "-")

    def _build_command(
        self, operation: BoundOperation, client: ApiClient
    ) -> click.Command:
        help_entry = CATALOG.get(operation.operation_id) or HelpEntry(
            short=operation.summary or operation.command_name,
            long=operation.description or operation.summary or operation.command_name,
            examples=[],
            params={},
        )
        params: list[click.Parameter] = []
        for parameter in operation.parameters:
            if parameter.location == "path":
                params.append(
                    click.Argument(
                        [parameter.name.replace("-", "_")],
                        required=True,
                        type=self._click_type(parameter.schema),
                    )
                )
                continue
            option_name = f"--{parameter.cli_name}"
            if self._is_bool(parameter.schema):
                params.append(
                    click.Option(
                        [option_name],
                        is_flag=True,
                        default=False,
                        help=help_entry.params.get(parameter.cli_name, ""),
                        show_default=True,
                    )
                )
                continue
            params.append(
                click.Option(
                    [option_name],
                    required=parameter.required,
                    multiple=self._is_array(parameter.schema),
                    type=self._click_type(parameter.schema),
                    help=help_entry.params.get(parameter.cli_name, ""),
                    default=() if self._is_array(parameter.schema) else None,
                )
            )
        if operation.request_body_content_type == "multipart/form-data":
            params.append(
                click.Option(
                    ["--body-file"],
                    type=click.Path(exists=True, dir_okay=False, path_type=Path),
                    required=True,
                    help=help_entry.params.get("body-file", ""),
                )
            )
        elif operation.request_body_schema is not None:
            params.extend(
                [
                    click.Option(
                        ["--body"], type=str, help=help_entry.params.get("body", "")
                    ),
                    click.Option(
                        ["--body-file"],
                        type=click.Path(exists=True, dir_okay=False, path_type=Path),
                        help=help_entry.params.get("body-file", ""),
                    ),
                    click.Option(
                        ["--field"],
                        multiple=True,
                        type=str,
                        help=help_entry.params.get("field", ""),
                    ),
                ]
            )
        if operation.produces_sse:
            params.extend(
                [
                    click.Option(
                        ["--max-events"],
                        type=int,
                        default=None,
                        help=help_entry.params.get("max-events", ""),
                    ),
                    click.Option(
                        ["--timeout"],
                        type=float,
                        default=None,
                        help=help_entry.params.get("timeout", ""),
                    ),
                    click.Option(
                        ["--raw"],
                        is_flag=True,
                        default=False,
                        help=help_entry.params.get("raw", ""),
                    ),
                ]
            )
        if operation.method == "DELETE":
            params.append(
                click.Option(
                    ["--yes"],
                    is_flag=True,
                    default=False,
                    help=help_entry.params.get("yes", ""),
                )
            )
        params.extend(self._shared_passthrough_options())

        epilog = "\n".join(
            filter(
                None,
                [
                    help_entry.long,
                    "Warnings:\n" + "\n".join(help_entry.warnings)
                    if help_entry.warnings
                    else "",
                    "Examples:\n" + "\n".join(help_entry.examples)
                    if help_entry.examples
                    else "",
                ],
            )
        )

        @click.pass_context
        def callback(ctx: click.Context, **kwargs: Any) -> None:
            del ctx
            self._invoke(operation, client, kwargs)

        return click.Command(
            name=operation.command_name,
            params=params,
            callback=callback,
            help=help_entry.short,
            epilog=epilog,
        )

    def _invoke(
        self,
        operation: BoundOperation,
        client: ApiClient,
        values: dict[str, Any],
    ) -> None:
        path_params: dict[str, Any] = {}
        query_params: dict[str, Any] = {}
        headers: dict[str, str] = {}
        body: Any | None = None
        for parameter in operation.parameters:
            key = parameter.name.replace("-", "_")
            value = values.pop(key, None)
            if value in (None, (), ""):
                continue
            if parameter.location == "path":
                path_params[parameter.name] = value
            elif parameter.location == "query":
                query_params[parameter.name] = (
                    ",".join(value) if isinstance(value, tuple) else value
                )
            elif parameter.location == "header":
                headers[parameter.name] = str(value)
        if operation.method == "DELETE" and not values.pop("yes", False):
            if not click.confirm("Delete this team?"):
                raise click.Abort()
        body_file = values.pop("body_file", None)
        if operation.request_body_content_type == "multipart/form-data":
            body = body_file
        elif operation.request_body_schema is not None:
            body = self._resolve_body(
                schema=operation.request_body_schema,
                body=values.pop("body", None),
                body_file=body_file,
                fields=values.pop("field", ()),
            )
        if operation.produces_sse:
            renderer = SseRenderer(client.settings)
            lines = client.stream(
                operation.path,
                path_params=path_params,
                query_params=query_params,
                headers=headers,
            )
            renderer.render(
                lines,
                raw=bool(values.pop("raw", False)),
                max_events=values.pop("max_events", None),
                timeout=values.pop("timeout", None),
            )
            return
        result = client.request(
            operation.method,
            operation.path,
            path_params=path_params,
            query_params=query_params,
            headers=headers,
            body=body,
            content_type=operation.request_body_content_type,
            file_field_name=self._body_file_field_name(operation.request_body_schema),
        )
        from cli.formatter import render_output

        render_output(result, client.settings)

    def _resolve_body(
        self,
        *,
        schema: dict[str, Any],
        body: str | None,
        body_file: Path | None,
        fields: tuple[str, ...],
    ) -> Any:
        if body is not None:
            return json.loads(body)
        if body_file is not None:
            return json.loads(body_file.read_text(encoding="utf-8"))
        built: dict[str, Any] = {}
        for field in fields:
            key, separator, value = field.partition("=")
            if not separator:
                raise click.BadParameter(f"Expected key=value, got: {field}")
            built[key] = self._coerce_field_value(
                schema.get("properties", {}).get(key, {}), value
            )
        return built if built else None

    def _coerce_field_value(self, schema: dict[str, Any], value: str) -> Any:
        if self._is_bool(schema):
            return value.lower() in {"1", "true", "yes", "on"}
        schema_type = schema.get("type")
        if schema_type == "integer":
            return int(value)
        if schema_type == "number":
            return float(value)
        if schema_type == "array":
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def _body_file_field_name(self, schema: dict[str, Any] | None) -> str | None:
        if schema is None:
            return None
        properties = schema.get("properties", {})
        if len(properties) == 1:
            return next(iter(properties))
        return None

    def _is_bool(self, schema: dict[str, Any]) -> bool:
        return schema.get("type") == "boolean"

    def _is_array(self, schema: dict[str, Any]) -> bool:
        return schema.get("type") == "array"

    def _click_type(self, schema: dict[str, Any]) -> click.ParamType | type[Any]:
        if "enum" in schema:
            return click.Choice([str(item) for item in schema["enum"]])
        schema_type = schema.get("type")
        if schema_type == "integer":
            return int
        if schema_type == "number":
            return float
        return str

    def _shared_passthrough_options(self) -> list[click.Option]:
        return [
            click.Option(["--format"], hidden=True, expose_value=False),
            click.Option(
                ["--quiet", "-q"], hidden=True, is_flag=True, expose_value=False
            ),
            click.Option(["--no-color"], hidden=True, is_flag=True, expose_value=False),
            click.Option(
                ["--verbose", "-v"], hidden=True, is_flag=True, expose_value=False
            ),
            click.Option(["--dry-run"], hidden=True, is_flag=True, expose_value=False),
            click.Option(["--base-url"], hidden=True, expose_value=False),
            click.Option(["--timeout"], hidden=True, expose_value=False),
            click.Option(
                ["--as"], "caller_agent_id_passthrough", hidden=True, expose_value=False
            ),
            click.Option(["--spec"], hidden=True, expose_value=False),
            click.Option(
                ["--refresh-spec"], hidden=True, is_flag=True, expose_value=False
            ),
            click.Option(["--offline"], hidden=True, is_flag=True, expose_value=False),
        ]

    def _resolve_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in schema:
            ref_name = str(schema["$ref"]).split("/")[-1]
            return self._resolve_schema(self.components.get(ref_name, {}))
        if "anyOf" in schema:
            for candidate in schema["anyOf"]:
                if candidate.get("type") != "null":
                    return self._resolve_schema(candidate)
        if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
            resolved_items = self._resolve_schema(schema["items"])
            return {**schema, "items": resolved_items}
        properties = schema.get("properties")
        if isinstance(properties, dict):
            return {
                **schema,
                "properties": {
                    key: self._resolve_schema(value)
                    for key, value in properties.items()
                },
            }
        return schema
