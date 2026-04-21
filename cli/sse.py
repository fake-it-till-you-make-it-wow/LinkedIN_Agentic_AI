"""SSE parsing and rendering.

[파일 역할]
- CLI에서 수신한 Server-Sent Events(SSE) 텍스트 스트림을 파싱하고 출력한다.
- `SseParser`는 라인 단위 SSE 프로토콜(event/data/id/retry)을 이벤트 객체로 조립한다.
- `SseRenderer`는 이벤트를 사람이 읽기 쉬운 형태(또는 raw 라인)로 터미널에 렌더링한다.

[사용 맥락]
- 실시간 데모/스트리밍 로그를 CLI에서 관찰할 때 사용한다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from rich.console import Console

from cli.config import Settings


@dataclass(slots=True)
class SseEvent:
    """One SSE event block."""

    event: str | None
    data: str
    id: str | None = None
    retry: int | None = None


class SseParser:
    """Incremental SSE line parser."""

    def __init__(self) -> None:
        self._event: str | None = None
        self._data_parts: list[str] = []
        self._id: str | None = None
        self._retry: int | None = None

    def feed(self, line: str) -> SseEvent | None:
        """Consume one line."""

        if line == "":
            if not self._data_parts:
                return None
            event = SseEvent(
                event=self._event,
                data="\n".join(self._data_parts),
                id=self._id,
                retry=self._retry,
            )
            self.__init__()
            return event
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        value = value.removeprefix(" ")
        if field == "event":
            self._event = value
        elif field == "data":
            self._data_parts.append(value)
        elif field == "id":
            self._id = value
        elif field == "retry":
            try:
                self._retry = int(value)
            except ValueError:
                self._retry = None
        return None


class SseRenderer:
    """Render SSE events to stdout."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.console = Console(no_color=settings.no_color)

    def render(
        self,
        lines: list[str],
        *,
        raw: bool = False,
        max_events: int | None = None,
        timeout: float | None = None,
    ) -> None:
        """Render raw SSE lines."""

        parser = SseParser()
        count = 0
        started_at = time.monotonic()
        for line in lines:
            if timeout is not None and time.monotonic() - started_at >= timeout:
                break
            if raw:
                self.console.print(line)
                if line.startswith("data:"):
                    count += 1
            else:
                event = parser.feed(line)
                if event is not None:
                    self._render_event(event)
                    count += 1
            if max_events is not None and count >= max_events:
                break

    def _render_event(self, event: SseEvent) -> None:
        label = event.event or "message"
        self.console.print(f"[{label}] {event.data}")
