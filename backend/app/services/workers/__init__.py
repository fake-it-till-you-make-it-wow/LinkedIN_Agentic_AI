"""Inline worker registry.

Phase 3-E에서 도입된 경로다. 기존에는 워커가 각자의 HTTP 서버
(:8001~:8004)로 실행되어야 했지만, 데모 용도로는 동일 로직을
백엔드 프로세스 안에서 순수 함수로 직접 호출한다.

`resolve_worker(endpoint_url)` 이 None을 반환하면 invoke/outreach
서비스는 기존처럼 HTTP 경로(`agents.common.post_json`)로 떨어진다.
따라서 배포 환경에서 워커를 다시 HTTP 프로세스로 분리해도 설정만
바꾸면 그대로 호환된다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend.app.services.workers import coder, designer, marketer, researcher

WorkerHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class InlineWorker:
    """Paired invoke/incoming handlers for a single worker persona."""

    __slots__ = ("incoming", "invoke", "label")

    def __init__(
        self,
        label: str,
        invoke_fn: WorkerHandler,
        incoming_fn: WorkerHandler,
    ) -> None:
        self.label = label
        self.invoke = invoke_fn
        self.incoming = incoming_fn


_INLINE_WORKERS: dict[str, InlineWorker] = {
    "http://127.0.0.1:8001": InlineWorker(
        "researcher", researcher.invoke, researcher.incoming
    ),
    "http://127.0.0.1:8002": InlineWorker("coder", coder.invoke, coder.incoming),
    "http://127.0.0.1:8003": InlineWorker(
        "marketer", marketer.invoke, marketer.incoming
    ),
    "http://127.0.0.1:8004": InlineWorker(
        "designer", designer.invoke, designer.incoming
    ),
}

# localhost ↔ 127.0.0.1 변형까지 동일하게 매핑
_ALIASES: dict[str, str] = {
    "http://localhost:8001": "http://127.0.0.1:8001",
    "http://localhost:8002": "http://127.0.0.1:8002",
    "http://localhost:8003": "http://127.0.0.1:8003",
    "http://localhost:8004": "http://127.0.0.1:8004",
}


def resolve_worker(endpoint_url: str | None) -> InlineWorker | None:
    """Return the inline worker for the given endpoint URL or None."""
    if not endpoint_url:
        return None
    normalized = endpoint_url.rstrip("/")
    normalized = _ALIASES.get(normalized, normalized)
    return _INLINE_WORKERS.get(normalized)


__all__ = ["InlineWorker", "resolve_worker"]
