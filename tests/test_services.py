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


@pytest.mark.asyncio()
async def test_invoke_agent_missing_target_raises(db_session) -> None:
    """TC-04-03: 존재하지 않는 target → InvokeServiceError."""

    from backend.app.services.invoke import InvokeServiceError

    caller = Agent(name="Caller", skill_tags=["pm"])
    db_session.add(caller)
    db_session.commit()

    with pytest.raises(InvokeServiceError, match="Agent not found"):
        await invoke_agent(
            db_session,
            caller.id,
            "00000000-0000-0000-0000-000000000000",
            {"query": "x"},
        )


@pytest.mark.asyncio()
async def test_invoke_agent_without_endpoint_raises(db_session) -> None:
    """TC-04-04: target endpoint_url 없음 → InvokeServiceError."""

    from backend.app.services.invoke import InvokeServiceError

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="NoEndpoint", skill_tags=["research"], endpoint_url=None)
    db_session.add_all([caller, target])
    db_session.commit()

    with pytest.raises(InvokeServiceError, match="엔드포인트"):
        await invoke_agent(db_session, caller.id, target.id, {"query": "x"})


@pytest.mark.asyncio()
async def test_send_outreach_missing_target_raises(db_session) -> None:
    """TC-05-03: 존재하지 않는 target → OutreachServiceError."""

    from backend.app.services.outreach import OutreachServiceError

    caller = Agent(name="Caller", skill_tags=["pm"])
    db_session.add(caller)
    db_session.commit()

    with pytest.raises(OutreachServiceError, match="Agent not found"):
        await send_outreach(
            db_session,
            caller.id,
            "00000000-0000-0000-0000-000000000000",
            "hi",
        )


@pytest.mark.asyncio()
async def test_send_outreach_without_endpoint_persists_system_message(
    db_session,
) -> None:
    """TC-05-04: endpoint 없을 때 Thread + 시스템 메시지 생성."""

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="NoEndpoint", skill_tags=["research"], endpoint_url=None)
    db_session.add_all([caller, target])
    db_session.commit()

    result = await send_outreach(db_session, caller.id, target.id, "합류 요청")
    assert result.status == "error"
    assert "엔드포인트가 없습니다" in result.response
    assert db_session.query(Thread).count() == 1
    assert db_session.query(Message).count() == 2


def test_search_agents_tool_orders_by_tag_match(db_session) -> None:
    """TC-09-02: MCP search_agents smoke test."""

    from backend.mcp_server import search_agents_tool

    db_session.add_all(
        [
            Agent(
                name="Researcher",
                skill_tags=["research"],
                star_rating=4.8,
                success_rate=0.95,
                avg_response_ms=900,
            ),
            Agent(
                name="Designer",
                skill_tags=["ui-design"],
                star_rating=4.9,
                success_rate=0.9,
                avg_response_ms=1100,
            ),
        ]
    )
    db_session.commit()

    results = search_agents_tool(tags=["research"], limit=5)
    assert results
    assert results[0]["name"] == "Researcher"
    assert results[0]["specialization_match"] == 1.0
    assert "final_score" in results[0]


def test_get_agent_profile_tool_returns_trust_score(db_session) -> None:
    """TC-09-03: MCP get_agent_profile smoke test."""

    from backend.mcp_server import get_agent_profile_tool

    target = Agent(name="Profile", skill_tags=["research"], star_rating=4.2)
    db_session.add(target)
    db_session.commit()

    profile = get_agent_profile_tool(target.id)
    assert profile["id"] == target.id
    assert profile["name"] == "Profile"
    assert "trust_score" in profile


def test_get_agent_profile_tool_missing_raises(db_session) -> None:
    """MCP get_agent_profile: 존재하지 않는 UUID → ValueError."""

    from backend.mcp_server import get_agent_profile_tool

    del db_session
    with pytest.raises(ValueError, match="Agent not found"):
        get_agent_profile_tool("00000000-0000-0000-0000-000000000000")


def test_research_agent_parser_extracts_summary_and_findings() -> None:
    """Research agent bullet parser: summary + 3 findings 추출."""

    from agents.agent_researcher import _parse_research_response

    raw = (
        "SUMMARY: AI 에이전트 시장은 자동화 수요로 성장 중.\n"
        "- 도메인 특화 에이전트가 유리하다\n"
        "- 검증된 퍼블리셔가 신뢰도를 높인다\n"
        "- 빠른 응답이 데모에서 중요하다"
    )
    summary, findings = _parse_research_response(raw)
    assert "자동화" in summary
    assert len(findings) == 3
    assert findings[0].startswith("도메인")


def test_research_agent_parser_handles_unstructured_text() -> None:
    """Bullet/summary 없으면 findings 빈 리스트."""

    from agents.agent_researcher import _parse_research_response

    summary, findings = _parse_research_response("free-form prose only")
    assert summary == ""
    assert findings == []
