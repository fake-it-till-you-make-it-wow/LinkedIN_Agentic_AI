"""OpenAPI spec loading and caching."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from cli.config import Settings, is_url
from cli.errors import NetworkError, SpecUnavailable

_TTL = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class SpecSource:
    """Metadata about the loaded spec."""

    kind: str
    location: str
    fetched_at: str | None


@dataclass(frozen=True, slots=True)
class LoadedSpec:
    """Resolved spec and source metadata."""

    spec: dict[str, Any]
    source: SpecSource


class SpecLoader:
    """Fetch, validate, and cache the OpenAPI spec."""

    def __init__(self, settings: Settings, http: httpx.Client) -> None:
        self.settings = settings
        self.http = http

    def load(self) -> LoadedSpec:
        """Load the OpenAPI spec."""

        if self.settings.spec_override:
            spec = self._load_override(self.settings.spec_override)
            self._validate(spec)
            return LoadedSpec(
                spec=spec,
                source=SpecSource(
                    kind="override",
                    location=self.settings.spec_override,
                    fetched_at=None,
                ),
            )

        if self._cache_fresh() and not self.settings.refresh_spec:
            spec = self._load_cache()
            self._validate(spec)
            meta = self._read_meta()
            return LoadedSpec(
                spec=spec,
                source=SpecSource(
                    kind="cache",
                    location=str(self.cache_path),
                    fetched_at=str(meta.get("fetched_at")),
                ),
            )

        if self.settings.offline:
            if self.cache_path.exists():
                spec = self._load_cache()
                self._validate(spec)
                meta = self._read_meta()
                return LoadedSpec(
                    spec=spec,
                    source=SpecSource(
                        kind="cache",
                        location=str(self.cache_path),
                        fetched_at=str(meta.get("fetched_at")),
                    ),
                )
            raise SpecUnavailable(
                "스펙 파일이 없습니다. --offline 을 해제하거나 --spec 으로 경로를 지정하세요."
            )

        spec = self._fetch_remote()
        self._validate(spec)
        self._write_cache(spec)
        meta = self._read_meta()
        return LoadedSpec(
            spec=spec,
            source=SpecSource(
                kind="remote",
                location=f"{self.settings.base_url}/openapi.json",
                fetched_at=str(meta.get("fetched_at")),
            ),
        )

    @property
    def cache_path(self) -> Path:
        return self.settings.cache_dir / "openapi.json"

    @property
    def meta_path(self) -> Path:
        return self.settings.cache_dir / "openapi.meta.json"

    def _load_override(self, override: str) -> dict[str, Any]:
        if is_url(override):
            try:
                response = self.http.get(override)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise NetworkError(f"스펙을 가져올 수 없습니다: {override}") from exc
            return response.json()

        path = Path(override)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise SpecUnavailable(f"스펙 파일을 읽을 수 없습니다: {path}") from exc
        except json.JSONDecodeError as exc:
            raise SpecUnavailable(
                "스펙 파일이 손상됐습니다. --refresh-spec 후 재시도하세요."
            ) from exc

    def _cache_fresh(self) -> bool:
        if not self.cache_path.exists() or not self.meta_path.exists():
            return False
        meta = self._read_meta()
        fetched_at_raw = meta.get("fetched_at")
        cached_base_url = meta.get("base_url")
        if (
            not isinstance(fetched_at_raw, str)
            or cached_base_url != self.settings.base_url
        ):
            return False
        try:
            fetched_at = datetime.fromisoformat(fetched_at_raw)
        except ValueError:
            return False
        return datetime.now(UTC) - fetched_at <= _TTL

    def _load_cache(self) -> dict[str, Any]:
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SpecUnavailable(
                "스펙 파일이 손상됐습니다. --refresh-spec 후 재시도하세요."
            ) from exc

    def _read_meta(self) -> dict[str, Any]:
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _fetch_remote(self) -> dict[str, Any]:
        url = f"{self.settings.base_url}/openapi.json"
        try:
            response = self.http.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise NetworkError(
                f"백엔드에 연결할 수 없습니다 ({self.settings.base_url}). uv run uvicorn backend.app.main:app --port 8000 로 기동하세요."
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(
                f"백엔드에 연결할 수 없습니다 ({self.settings.base_url}). uv run uvicorn backend.app.main:app --port 8000 로 기동하세요."
            ) from exc
        return response.json()

    def _write_cache(self, spec: dict[str, Any]) -> None:
        self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.meta_path.write_text(
            json.dumps(
                {
                    "fetched_at": datetime.now(UTC).isoformat(),
                    "base_url": self.settings.base_url,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _validate(self, spec: dict[str, Any]) -> None:
        if "openapi" not in spec or "paths" not in spec:
            raise SpecUnavailable(
                "스펙 파일이 손상됐습니다. --refresh-spec 후 재시도하세요."
            )
        if not isinstance(spec["paths"], dict):
            raise SpecUnavailable(
                "스펙 파일이 손상됐습니다. --refresh-spec 후 재시도하세요."
            )
