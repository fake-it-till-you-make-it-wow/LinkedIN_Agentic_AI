"""Service and MCP-level tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models import Agent, InvokeLog, Message, Thread
from backend.app.services.invoke import invoke_agent
from backend.app.services.outreach import send_outreach


@pytest.mark.asyncio()
async def test_invoke_agent_success(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post_json(
        url: str, payload: dict, timeout: float = 30.0
    ) -> dict[str, str]:
        del url, payload, timeout
        return {"summary": "ok"}

    monkeypatch.setattr("backend.app.services.invoke.post_json", fake_post_json)

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"], endpoint_url="http://worker")
    db_session.add_all([caller, target])
    db_session.commit()

    result = await invoke_agent(db_session, caller.id, target.id, {"query": "hello"})
    assert result.status == "success"
    assert result.output == {"summary": "ok"}
    log = db_session.scalar(
        select(InvokeLog).where(InvokeLog.id == result.invoke_log_id)
    )
    assert log is not None
    assert db_session.get(Agent, target.id).total_calls == 1


@pytest.mark.asyncio()
async def test_invoke_agent_timeout(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post_json(
        url: str, payload: dict, timeout: float = 30.0
    ) -> dict[str, str]:
        del url, payload, timeout
        raise httpx.TimeoutException("timeout")

    import httpx

    monkeypatch.setattr("backend.app.services.invoke.post_json", fake_post_json)

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"], endpoint_url="http://worker")
    db_session.add_all([caller, target])
    db_session.commit()

    result = await invoke_agent(
        db_session, caller.id, target.id, {"query": "hello"}, timeout_ms=1
    )
    assert result.status == "timeout"
    assert result.output is None
    log = db_session.scalar(
        select(InvokeLog).where(InvokeLog.id == result.invoke_log_id)
    )
    assert log is not None
    assert log.status == "timeout"


@pytest.mark.asyncio()
async def test_send_outreach_reuses_thread(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post_json(
        url: str, payload: dict, timeout: float = 30.0
    ) -> dict[str, str]:
        del url, payload, timeout
        return {"response": "합류하겠습니다."}

    monkeypatch.setattr("backend.app.services.outreach.post_json", fake_post_json)

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"], endpoint_url="http://worker")
    db_session.add_all([caller, target])
    db_session.commit()

    first = await send_outreach(db_session, caller.id, target.id, "첫 메시지")
    second = await send_outreach(db_session, caller.id, target.id, "두 번째 메시지")
    assert first.thread_id == second.thread_id
    assert db_session.query(Thread).count() == 1
    assert db_session.query(Message).count() == 4


@pytest.mark.asyncio()
async def test_send_outreach_endpoint_error_persists_system_message(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_post_json(
        url: str, payload: dict, timeout: float = 30.0
    ) -> dict[str, str]:
        del url, payload, timeout
        raise RuntimeError("worker unavailable")

    monkeypatch.setattr("backend.app.services.outreach.post_json", fake_post_json)

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"], endpoint_url="http://worker")
    db_session.add_all([caller, target])
    db_session.commit()

    result = await send_outreach(db_session, caller.id, target.id, "첫 메시지")
    assert result.status == "error"
    assert "메시지 전달 실패" in result.response
    assert db_session.query(Thread).count() == 1
    assert db_session.query(Message).count() == 2


def test_submit_review_requires_invoke_history(db_session) -> None:
    from backend.mcp_server import submit_review_tool

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"])
    db_session.add_all([caller, target])
    db_session.commit()

    result = submit_review_tool(caller.id, target.id, 4.5, "good")
    assert result["success"] is False
    assert "호출 이력이 없어" in result["error"]


def test_submit_review_rejects_invalid_rating(db_session) -> None:
    from backend.mcp_server import submit_review_tool

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"])
    db_session.add_all([caller, target])
    db_session.commit()

    result = submit_review_tool(caller.id, target.id, 6.0, "bad range")
    assert result["success"] is False
    assert "0.0 ~ 5.0" in result["error"]


def test_submit_review_updates_rating(db_session) -> None:
    from backend.mcp_server import submit_review_tool

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"], star_rating=4.0)
    db_session.add_all([caller, target])
    db_session.flush()
    db_session.add(
        InvokeLog(
            caller_id=caller.id,
            target_id=target.id,
            input_data={"query": "x"},
            output_data={"summary": "y"},
            status="success",
            response_ms=100,
        )
    )
    db_session.commit()

    result = submit_review_tool(caller.id, target.id, 5.0, "great")
    assert result["success"] is True
    assert result["new_star_rating"] == 4.5
