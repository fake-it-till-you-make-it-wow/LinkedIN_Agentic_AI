"""Invoke service logic."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx
from sqlalchemy.orm import Session

from agents.common import post_json
from backend.app.models import Agent, InvokeLog
from backend.app.schemas import InvokeResult


class InvokeServiceError(Exception):
    """Raised when an invoke request cannot be processed."""


async def invoke_agent(
    session: Session,
    caller_agent_id: str,
    target_agent_id: str,
    input_data: dict[str, Any],
    timeout_ms: int = 30000,
) -> InvokeResult:
    """Invoke a worker agent and persist an invoke log."""

    caller = session.get(Agent, caller_agent_id)
    target = session.get(Agent, target_agent_id)
    if caller is None or target is None:
        raise InvokeServiceError("Agent not found")
    if not target.endpoint_url:
        raise InvokeServiceError("대상 에이전트에 엔드포인트가 없습니다")

    started = perf_counter()
    status = "success"
    output: dict[str, Any] | None = None
    response_ms = 0

    try:
        output = await post_json(
            f"{target.endpoint_url.rstrip('/')}/invoke",
            input_data,
            timeout=timeout_ms / 1000,
        )
        response_ms = int((perf_counter() - started) * 1000)
        target.total_calls += 1
    except httpx.TimeoutException:
        status = "timeout"
        response_ms = timeout_ms
    except Exception:
        status = "error"
        response_ms = int((perf_counter() - started) * 1000)

    log = InvokeLog(
        caller_id=caller.id,
        target_id=target.id,
        input_data=input_data,
        output_data=output,
        status=status,
        response_ms=response_ms,
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return InvokeResult(
        invoke_log_id=log.id,
        output=output,
        status=status,
        response_ms=response_ms,
    )
