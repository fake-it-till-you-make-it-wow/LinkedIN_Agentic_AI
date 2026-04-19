"""Phase 3-E live demo SSE router."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.app.database import get_session_factory
from backend.app.services.demo_events import DemoEventEmitter
from backend.app.services.demo_runner import run_demo

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/stream")
async def demo_stream() -> StreamingResponse:
    """SSE 스트림. 연결되면 5막 PM 데모를 실행하며 이벤트를 송출한다.

    브라우저에서는 `new EventSource('/api/demo/stream')` 로 구독한다.
    각 이벤트는 `event: <type>\\ndata: <json>\\n\\n` 형식으로 전송된다.
    데모가 완료되거나 에러가 발생하면 `finale` 또는 `error` 이벤트 뒤에
    서버가 스트림을 닫는다.
    """

    emitter = DemoEventEmitter()
    session_factory = get_session_factory()

    async def event_gen() -> AsyncIterator[str]:
        runner_task = asyncio.create_task(run_demo(session_factory, emitter))
        try:
            async for event in emitter.iter_events():
                payload = json.dumps(event.data, ensure_ascii=False, default=str)
                yield f"event: {event.type}\ndata: {payload}\n\n"
        finally:
            if not runner_task.done():
                runner_task.cancel()
            # demo_runner 내부에서 모든 예외를 "error" 이벤트로 변환했거나
            # 클라이언트가 연결을 끊어 task가 cancel된 경우다. 두 경우 모두
            # 추가 로깅 없이 조용히 종료한다.
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await runner_task

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_gen(), media_type="text/event-stream", headers=headers
    )
