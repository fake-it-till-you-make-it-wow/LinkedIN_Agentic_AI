"""Invoke service logic."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from agents.common import post_json
from backend.app.models import Agent, InvokeLog
from backend.app.schemas import InvokeResult
from backend.app.services.demo_events import DemoEventEmitter
from backend.app.services.workers import resolve_worker


class InvokeServiceError(Exception):
    """Raised when an invoke request cannot be processed."""


def _recompute_target_metrics(session: Session, target: Agent) -> None:
    """Refresh dynamic trust metrics from InvokeLog aggregates."""

    total, successes = session.execute(
        select(
            func.count(InvokeLog.id),
            func.sum(case((InvokeLog.status == "success", 1), else_=0)),
        ).where(InvokeLog.target_id == target.id)
    ).one()
    if not total:
        return
    target.success_rate = round((successes or 0) / total, 4)
    avg_ms = session.scalar(
        select(func.avg(InvokeLog.response_ms)).where(
            InvokeLog.target_id == target.id,
            InvokeLog.status == "success",
        )
    )
    if avg_ms is not None:
        target.avg_response_ms = int(avg_ms)


async def invoke_agent(
    session: Session,
    caller_agent_id: str,
    target_agent_id: str,
    input_data: dict[str, Any],
    timeout_ms: int = 30000,
    emitter: DemoEventEmitter | None = None,
) -> InvokeResult:
    """Invoke a worker agent and persist an invoke log.

    `emitter`가 주어지면 Phase 3-E 데모용 라이브 이벤트를 방출한다
    (`invoke_sent`, `invoke_completed`). 워커의 endpoint_url이 인라인
    레지스트리와 매칭되면 HTTP 호출 대신 같은 프로세스 안의 순수 함수를
    직접 호출한다. 매칭되지 않으면 기존처럼 `post_json`으로 떨어진다.
    """

    caller = session.get(Agent, caller_agent_id)
    target = session.get(Agent, target_agent_id)
    if caller is None or target is None:
        raise InvokeServiceError("Agent not found")
    if not target.endpoint_url:
        raise InvokeServiceError("대상 에이전트에 엔드포인트가 없습니다")

    worker = resolve_worker(target.endpoint_url)
    transport = "inline" if worker is not None else "http"

    if emitter is not None:
        await emitter.emit(
            "invoke_sent",
            {
                "from": {"id": caller.id, "name": caller.name},
                "to": {"id": target.id, "name": target.name},
                "input": input_data,
                "transport": transport,
            },
        )

    started = perf_counter()
    status = "success"
    output: dict[str, Any] | None = None
    response_ms = 0

    try:
        if worker is not None:
            output = await worker.invoke(input_data)
        else:
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
    session.flush()
    _recompute_target_metrics(session, target)
    session.commit()
    session.refresh(log)

    if emitter is not None:
        await emitter.emit(
            "invoke_completed",
            {
                "agent": {"id": target.id, "name": target.name},
                "status": status,
                "output": output,
                "response_ms": response_ms,
            },
        )

    return InvokeResult(
        invoke_log_id=log.id,
        output=output,
        status=status,
        response_ms=response_ms,
    )
