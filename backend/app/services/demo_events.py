"""Demo live-log event emitter.

Phase 3-E "Live Demo MVP"에서 SSE 스트림으로 전달할 이벤트를
서비스 레이어에서 방출하기 위한 경량 큐 기반 emitter다.

설계 요점:
- `DemoEventEmitter` 인스턴스 하나가 하나의 SSE 연결(= 하나의 데모 실행)에 대응
- `invoke_agent` / `send_outreach` 는 선택적 `emitter` 파라미터를 받아
  진행 중 이벤트를 push. emitter가 None이면 기존 동작과 완전히 동일
- SSE 라우터는 `iter_events()` 를 async-for로 소비하며 브라우저에 전달
- 데모 종료 시 `close()` 호출로 sentinel(None) 을 큐에 넣어 소비자 종료
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DemoEvent:
    """하나의 라이브 로그 이벤트."""

    type: str
    data: dict[str, Any]


class DemoEventEmitter:
    """Asyncio 큐 기반 이벤트 방출기.

    스레드 안전성은 대상 범위 밖. 동일 이벤트 루프 안에서만 사용한다.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[DemoEvent | None] = asyncio.Queue()
        self._closed = False

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """이벤트를 큐에 넣는다. 닫힌 emitter에는 무시."""
        if self._closed:
            return
        await self._queue.put(DemoEvent(event_type, data))

    def close(self) -> None:
        """소비자 종료를 위해 sentinel을 넣는다. 멱등."""
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(None)

    async def iter_events(self) -> AsyncIterator[DemoEvent]:
        """이벤트를 순서대로 yield. sentinel을 만나면 종료."""
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event


__all__ = ["DemoEvent", "DemoEventEmitter"]
