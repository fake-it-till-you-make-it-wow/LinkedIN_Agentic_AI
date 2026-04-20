"""Outreach service logic."""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from agents.common import post_json
from backend.app.models import Agent, Message, Thread
from backend.app.schemas import OutreachResult
from backend.app.services.demo_events import DemoEventEmitter
from backend.app.services.workers import resolve_worker


class OutreachServiceError(Exception):
    """Raised when an outreach request cannot be processed."""


async def _incoming_as_persona(target: Agent, caller_name: str, message: str) -> str:
    """endpoint가 없는 에이전트를 위한 persona 기반 Groq 수락 응답."""
    from agents.common import chat

    skills = ", ".join(target.skill_tags or [])
    system = f"You are {target.name}. {target.description or ''} Expertise: {skills}."
    prompt = (
        f"{caller_name}님으로부터 팀 합류 제안을 받았습니다: {message}\n"
        "1-2 문장으로 전문성을 살린 수락 응답을 한국어로 작성하세요."
    )
    try:
        return await chat(system, prompt)
    except Exception:
        return (
            f"안녕하세요, {caller_name}님. "
            f"말씀하신 역할로 팀에 합류하겠습니다. 함께 좋은 결과를 만들어 봐요!"
        )


def _thread_subject(caller: Agent, target: Agent) -> str:
    return f"{caller.name} → {target.name} outreach"


def _get_or_create_thread(session: Session, caller: Agent, target: Agent) -> Thread:
    statement = (
        select(Thread)
        .where(Thread.initiator_id == caller.id, Thread.target_id == target.id)
        .options(selectinload(Thread.messages))
    )
    thread = session.scalar(statement)
    if thread is not None:
        return thread

    thread = Thread(
        initiator_id=caller.id,
        target_id=target.id,
        subject=_thread_subject(caller, target),
    )
    session.add(thread)
    session.flush()
    return thread


async def send_outreach(
    session: Session,
    caller_agent_id: str,
    target_agent_id: str,
    message: str,
    emitter: DemoEventEmitter | None = None,
) -> OutreachResult:
    """Persist outreach messages and forward them to the worker endpoint.

    `emitter`가 주어지면 Phase 3-E 데모용 라이브 이벤트를 방출한다
    (`dm_sent`, `dm_received`). 워커가 인라인 레지스트리에 등록되어
    있으면 HTTP 호출 대신 같은 프로세스 안의 함수를 직접 호출한다.
    """

    caller = session.get(Agent, caller_agent_id)
    target = session.get(Agent, target_agent_id)
    if caller is None or target is None:
        raise OutreachServiceError("Agent not found")

    thread = _get_or_create_thread(session, caller, target)
    session.add(Message(thread_id=thread.id, sender_id=caller.id, content=message))

    worker = resolve_worker(target.endpoint_url)
    transport = (
        "inline" if worker is not None else ("http" if target.endpoint_url else "none")
    )

    if emitter is not None:
        await emitter.emit(
            "dm_sent",
            {
                "thread_id": thread.id,
                "from": {"id": caller.id, "name": caller.name},
                "to": {"id": target.id, "name": target.name},
                "message": message,
                "transport": transport,
            },
        )

    status = "success"
    response_text = ""
    if worker is not None:
        try:
            response = await worker.incoming(
                {
                    "thread_id": thread.id,
                    "from_agent": {"id": caller.id, "name": caller.name},
                    "message": message,
                }
            )
            response_text = str(response.get("response", ""))
        except Exception as exc:
            status = "error"
            response_text = f"[시스템] 메시지 전달 실패: {exc}"
    elif not target.endpoint_url:
        response_text = await _incoming_as_persona(target, caller.name, message)
    else:
        try:
            payload = {
                "thread_id": thread.id,
                "from_agent": {"id": caller.id, "name": caller.name},
                "message": message,
            }
            response = await post_json(
                f"{target.endpoint_url.rstrip('/')}/incoming",
                payload,
                timeout=30.0,
            )
            response_text = str(response.get("response", ""))
        except httpx.TimeoutException:
            status = "error"
            response_text = "[시스템] 메시지 전달 실패: timeout"
        except Exception as exc:
            status = "error"
            response_text = f"[시스템] 메시지 전달 실패: {exc}"

    session.add(
        Message(thread_id=thread.id, sender_id=target.id, content=response_text)
    )
    session.commit()
    session.refresh(thread)

    if emitter is not None:
        await emitter.emit(
            "dm_received",
            {
                "thread_id": thread.id,
                "from": {"id": target.id, "name": target.name},
                "to": {"id": caller.id, "name": caller.name},
                "response": response_text,
                "status": status,
            },
        )

    return OutreachResult(thread_id=thread.id, response=response_text, status=status)
