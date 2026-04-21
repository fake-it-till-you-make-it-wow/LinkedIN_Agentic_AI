"""HTTP client wrapper for the Ocean CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from cli.config import Settings
from cli.errors import HttpClientError, HttpServerError, NetworkError


class ApiClient:
    """Backend client."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.Client(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            follow_redirects=True,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, Any],
        query_params: dict[str, Any],
        headers: dict[str, str],
        body: Any | None,
        content_type: str | None = None,
        file_field_name: str | None = None,
    ) -> Any:
        """Perform one HTTP request."""

        resolved_path = path.format(**path_params)
        request_kwargs = self._build_request_kwargs(
            query_params=query_params,
            headers=headers,
            body=body,
            content_type=content_type,
            file_field_name=file_field_name,
        )
        if self.settings.dry_run:
            return self._build_curl(method, resolved_path, request_kwargs)
        try:
            response = self.http.request(method, resolved_path, **request_kwargs)
        except httpx.TimeoutException as exc:
            raise NetworkError(
                f"백엔드에 연결할 수 없습니다 ({self.settings.base_url}). uv run uvicorn backend.app.main:app --port 8000 로 기동하세요."
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(
                f"백엔드에 연결할 수 없습니다 ({self.settings.base_url}). uv run uvicorn backend.app.main:app --port 8000 로 기동하세요."
            ) from exc
        return self._unwrap_response(response)

    def stream(
        self,
        path: str,
        *,
        path_params: dict[str, Any],
        query_params: dict[str, Any],
        headers: dict[str, str],
    ) -> list[str]:
        """Return raw streamed lines."""

        resolved_path = path.format(**path_params)
        try:
            with self.http.stream(
                "GET", resolved_path, params=query_params, headers=headers
            ) as response:
                if response.status_code >= 400:
                    self._raise_for_status(response)
                return [line for line in response.iter_lines() if line is not None]
        except httpx.HTTPError as exc:
            raise NetworkError(
                f"백엔드에 연결할 수 없습니다 ({self.settings.base_url}). uv run uvicorn backend.app.main:app --port 8000 로 기동하세요."
            ) from exc

    def close(self) -> None:
        """Close the underlying client."""

        self.http.close()

    def _build_request_kwargs(
        self,
        *,
        query_params: dict[str, Any],
        headers: dict[str, str],
        body: Any | None,
        content_type: str | None,
        file_field_name: str | None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"params": query_params, "headers": headers}
        if content_type == "multipart/form-data" and isinstance(body, Path):
            field_name = file_field_name or "file"
            kwargs["files"] = {field_name: (body.name, body.read_bytes())}
            return kwargs
        if body is None:
            return kwargs
        if content_type == "application/json" or isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["content"] = body
        return kwargs

    def _unwrap_response(self, response: httpx.Response) -> Any:
        self._raise_for_status(response)
        if response.headers.get("content-type", "").startswith("text/"):
            return response.text
        if response.status_code == 204 or not response.content:
            return {"status": "ok"}
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def _raise_for_status(self, response: httpx.Response) -> None:
        if 400 <= response.status_code < 500:
            raise HttpClientError(self._error_message(response))
        if response.status_code >= 500:
            raise HttpServerError(self._error_message(response))

    def _error_message(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = response.text
        return f"{response.status_code} {payload}"

    def _build_curl(
        self, method: str, resolved_path: str, request_kwargs: dict[str, Any]
    ) -> str:
        parts = [
            "curl",
            "-X",
            method.upper(),
            f"{self.settings.base_url}{resolved_path}",
        ]
        for key, value in request_kwargs.get("headers", {}).items():
            parts.extend(["-H", f"{key}: {value}"])
        for key, value in request_kwargs.get("params", {}).items():
            parts.extend(["-G", "--data-urlencode", f"{key}={value}"])
        if "json" in request_kwargs:
            parts.extend(["-H", "Content-Type: application/json"])
            parts.extend(
                ["--data", json.dumps(request_kwargs["json"], ensure_ascii=False)]
            )
        if "content" in request_kwargs:
            parts.extend(["--data", str(request_kwargs["content"])])
        if "files" in request_kwargs:
            for name, (filename, _) in request_kwargs["files"].items():
                parts.extend(["-F", f"{name}=@{filename}"])
        return " ".join(parts)
