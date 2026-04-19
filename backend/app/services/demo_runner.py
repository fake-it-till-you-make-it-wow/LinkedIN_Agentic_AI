"""5막 PM 데모를 서버사이드에서 실행하며 라이브 이벤트를 방출한다.

Phase 3-E에서 `agents/agent_pm.py`의 플로우를 재사용하기 위해 만든
모듈이다. 터미널 Rich 출력 대신 DemoEventEmitter로 이벤트를 push하며,
MCP SSE 클라이언트 대신 서비스 레이어를 직접 호출한다. 이 모듈은
HTTP 워커(:8001~:8004)가 기동되어 있지 않아도 backend/app/services/workers
레지스트리 경유로 같은 결과를 낸다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.models import Agent
from backend.app.schemas import AgentRead
from backend.app.services.demo_events import DemoEventEmitter
from backend.app.services.invoke import InvokeServiceError, invoke_agent
from backend.app.services.outreach import OutreachServiceError, send_outreach
from backend.app.services.scoring import compute_scores

MISSION = "AI 스타트업을 위한 리서치 + 개발 드림팀 구성"

RESEARCH_WEIGHTS: dict[str, float] = {
    "star_rating": 0.5,
    "response_speed": 0.3,
    "specialization": 0.2,
}
CODE_WEIGHTS: dict[str, float] = {
    "star_rating": 0.4,
    "response_speed": 0.2,
    "specialization": 0.4,
}

RESEARCH_QUERY = "AI startup market trends for autonomous agent platforms"
CODE_INPUT: dict[str, Any] = {
    "language": "python",
    "code": (
        "def build_team(agent_scores):\n    return sorted(agent_scores, reverse=True)"
    ),
}

RESEARCH_OUTREACH = "리서치 결과가 좋습니다. 팀에 합류해주시겠어요?"
CODE_OUTREACH = "코드 품질과 아키텍처 검토를 맡아 팀에 합류해주세요."

# Act 간 공백을 만들기 위한 작은 pacing (UI가 숨 쉴 시간).
# LLM 호출은 자체 지연이 있어 추가 sleep 불필요한 구간이 많다.
SHORT_PAUSE = 0.35
MEDIUM_PAUSE = 0.7


async def _pause(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _serialize_scored(agents_scored: list[Any]) -> list[dict[str, Any]]:
    """Convert compute_scores output into JSON-safe dicts for SSE transport."""

    rows: list[dict[str, Any]] = []
    for item in agents_scored:
        payload = AgentRead.model_validate(item.agent).model_dump(mode="json")
        payload["specialization_match"] = round(item.specialization_match, 4)
        payload["semantic_score"] = round(item.semantic_score, 4)
        payload["final_score"] = round(item.final_score, 4)
        rows.append(payload)
    return rows


async def _run_search_act(
    session_factory: sessionmaker[Any],
    emitter: DemoEventEmitter,
    *,
    act: int,
    title: str,
    tags: list[str],
    weights: dict[str, float],
) -> tuple[str, str]:
    """Search-stage sub-flow. Emits search + selection events and returns the pick."""

    await emitter.emit(
        "search_started",
        {"act": act, "title": title, "tags": tags, "weights": weights},
    )
    await _pause(SHORT_PAUSE)

    with session_factory() as session:
        agents = list(session.scalars(select(Agent)).all())
        scored = compute_scores(agents, tags, weights)[:5]
        rows = _serialize_scored(scored)

    if not rows:
        await emitter.emit(
            "error",
            {"stage": f"act{act}_search", "message": "검색 결과가 없습니다"},
        )
        raise RuntimeError("No candidates found")

    await emitter.emit(
        "search_completed",
        {"act": act, "title": title, "rows": rows},
    )
    await _pause(MEDIUM_PAUSE)

    top = rows[0]
    await emitter.emit(
        "selection",
        {
            "act": act,
            "agent": {"id": top["id"], "name": top["name"]},
            "score": top["final_score"],
            "reason": (
                f"가중치 기반 최고 점수 ({top['final_score']:.2f}). "
                f"별점 {top['star_rating']:.1f} · 응답 {top['avg_response_ms']}ms · "
                f"전문성 {top['specialization_match']:.2f}"
            ),
        },
    )
    await _pause(SHORT_PAUSE)

    return str(top["id"]), str(top["name"])


async def _run_invoke_act(
    session_factory: sessionmaker[Any],
    emitter: DemoEventEmitter,
    pm_id: str,
    target_id: str,
    input_data: dict[str, Any],
) -> None:
    with session_factory() as session:
        try:
            await invoke_agent(session, pm_id, target_id, input_data, emitter=emitter)
        except InvokeServiceError as exc:
            await emitter.emit("error", {"stage": "invoke", "message": str(exc)})
            raise
    await _pause(SHORT_PAUSE)


async def _run_outreach_act(
    session_factory: sessionmaker[Any],
    emitter: DemoEventEmitter,
    pm_id: str,
    target_id: str,
    message: str,
) -> None:
    with session_factory() as session:
        try:
            await send_outreach(session, pm_id, target_id, message, emitter=emitter)
        except OutreachServiceError as exc:
            await emitter.emit("error", {"stage": "outreach", "message": str(exc)})
            raise
    await _pause(SHORT_PAUSE)


async def run_demo(
    session_factory: sessionmaker[Any], emitter: DemoEventEmitter
) -> None:
    """Execute the full 5-act PM demo, emitting events along the way.

    예외는 내부에서 잡아 "error" 이벤트로 변환한다. finally 블록에서
    emitter.close() 를 호출하므로, 호출자는 단지 이 coroutine을 await
    하거나 background task로 돌리면 된다.
    """

    try:
        with session_factory() as session:
            pm = session.scalar(select(Agent).where(Agent.name == "PM Youngsu"))
            if pm is None:
                await emitter.emit(
                    "error",
                    {
                        "stage": "setup",
                        "message": (
                            "PM Youngsu seed가 없습니다. "
                            "`uv run python -m backend.seed` 로 시드를 먼저 등록하세요."
                        ),
                    },
                )
                return
            pm_id = pm.id
            pm_name = pm.name

        await emitter.emit(
            "mission_brief",
            {
                "act": 1,
                "title": "Act 1 — Mission Brief",
                "pm": {"id": pm_id, "name": pm_name},
                "mission": MISSION,
            },
        )
        await _pause(MEDIUM_PAUSE)

        await emitter.emit(
            "act_transition", {"to": 2, "label": "리서치 에이전트 탐색·위임·섭외"}
        )
        research_id, research_name = await _run_search_act(
            session_factory,
            emitter,
            act=2,
            title="Act 2 — 가중치 기반 리서치 탐색",
            tags=["research"],
            weights=RESEARCH_WEIGHTS,
        )
        await _run_invoke_act(
            session_factory,
            emitter,
            pm_id,
            research_id,
            {"query": RESEARCH_QUERY},
        )
        await _run_outreach_act(
            session_factory, emitter, pm_id, research_id, RESEARCH_OUTREACH
        )

        await emitter.emit(
            "act_transition", {"to": 5, "label": "코드 에이전트 탐색·위임·섭외"}
        )
        code_id, code_name = await _run_search_act(
            session_factory,
            emitter,
            act=5,
            title="Act 5 — 코드 에이전트 탐색",
            tags=["code-review", "python"],
            weights=CODE_WEIGHTS,
        )
        await _run_invoke_act(session_factory, emitter, pm_id, code_id, CODE_INPUT)
        await _run_outreach_act(session_factory, emitter, pm_id, code_id, CODE_OUTREACH)

        await emitter.emit(
            "finale",
            {
                "mission_complete": True,
                "team": [
                    {"id": pm_id, "name": pm_name, "role": "오케스트레이터"},
                    {"id": research_id, "name": research_name, "role": "리서치"},
                    {"id": code_id, "name": code_name, "role": "엔지니어링"},
                ],
                "stats": {
                    "searches": 2,
                    "invokes": 2,
                    "dms": 2,
                    "human_intervention": 0,
                },
            },
        )
    except RuntimeError:
        # _run_search_act already emitted an error event before raising.
        pass
    except Exception as exc:
        await emitter.emit("error", {"stage": "runtime", "message": str(exc)})
    finally:
        emitter.close()


__all__ = ["run_demo"]
