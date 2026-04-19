"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] MCP 서버 — AI 에이전트용 도구(Tool) 제공 서버
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【MCP란?】
  MCP(Model Context Protocol)는 AI 에이전트가 외부 도구를 호출할 수 있게 해주는 표준 프로토콜입니다.
  이 파일은 FastMCP 라이브러리로 MCP 서버를 구성하여
  PM 에이전트(agent_pm.py)가 원격으로 호출할 수 있는 도구 6개를 노출합니다.

【서버 실행 명령어】
  uv run python backend/mcp_server.py
  → 기본적으로 http://localhost:8100 에서 SSE 방식으로 동작합니다.

【노출되는 도구(Tool) 목록】
  ┌─────────────────────┬────────────────────────────────────────────────────┐
  │ 도구 이름           │ 기능                                               │
  ├─────────────────────┼────────────────────────────────────────────────────┤
  │ search_agents       │ 조건(태그·가중치)으로 에이전트를 검색하고 순위 반환│
  │ get_agent_profile   │ 특정 에이전트의 상세 프로필 조회                   │
  │ invoke_agent        │ 에이전트를 실제로 호출하여 작업을 위임              │
  │ send_outreach       │ 에이전트에게 협업 제안 DM 전송                     │
  │ get_my_threads      │ 특정 에이전트의 DM 대화 목록 조회                  │
  │ submit_review       │ 호출한 에이전트에 대한 별점 리뷰 등록              │
  └─────────────────────┴────────────────────────────────────────────────────┘

【데이터 흐름】
  PM 에이전트(agent_pm.py)
    → SSE 연결 (http://localhost:8100)
    → MCP 도구 호출 (예: search_agents)
    → 이 파일의 도구 함수 실행
    → DB 조회/업데이트 (SQLite)
    → 결과 반환

【관련 파일】
  - agents/agent_pm.py          : 이 MCP 서버를 사용하는 PM 오케스트레이터
  - backend/app/services/scoring.py  : 검색 가중치 계산 로직
  - backend/app/services/invoke.py   : 에이전트 호출 로직
  - backend/app/services/outreach.py : 아웃리치 메시지 전송 로직
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.config import get_settings
from backend.app.database import configure_database, get_session_factory, init_database
from backend.app.models import Agent, InvokeLog, Review, Thread
from backend.app.schemas import AgentRead, ReviewResult
from backend.app.services.invoke import InvokeServiceError, invoke_agent
from backend.app.services.outreach import OutreachServiceError, send_outreach
from backend.app.services.scoring import compute_scores

# 별점 최대값 (0.0 ~ 5.0)
MAX_RATING = 5.0


# ──────────────────────────────────────────────
# 내부 유틸 함수
# ──────────────────────────────────────────────


def _session() -> Session:
    """새로운 DB 세션을 생성한다. 각 도구 함수 호출마다 독립 세션 사용."""
    return get_session_factory()()


def _agent_or_none(session: Session, agent_id: str) -> Agent | None:
    """agent_id로 에이전트를 조회한다. 존재하지 않으면 None 반환."""
    return session.get(Agent, agent_id)


# ──────────────────────────────────────────────
# 도구 구현 함수 (내부 로직)
# ──────────────────────────────────────────────


def search_agents_tool(
    query: str = "",
    tags: list[str] | None = None,
    weights: dict[str, float] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """에이전트를 검색하고 가중치 기반 점수로 정렬하여 반환한다.

    【처리 순서】
      1. DB에서 모든 에이전트 조회
      2. query 텍스트가 있으면 이름·설명·퍼블리셔명으로 필터링
      3. compute_scores()로 각 에이전트에 가중치 점수 계산
      4. 점수 내림차순으로 상위 limit개 반환

    Args:
        query   : 검색어 (이름, 설명, 퍼블리셔명에서 검색)
        tags    : 필터링할 기술 태그 목록 (예: ["research", "python"])
        weights : 각 지표의 가중치 (예: {"star_rating": 0.5, "response_speed": 0.3})
        limit   : 반환할 최대 에이전트 수 (기본: 5)

    Returns:
        AgentRead 필드 + specialization_match + semantic_score + final_score 포함한 딕셔너리 목록
    """
    with _session() as session:
        # 모든 에이전트 로드
        agents = list(session.scalars(select(Agent)).all())

        # 텍스트 검색 필터링 (대소문자 무시)
        if query:
            lowered = query.lower()
            agents = [
                agent
                for agent in agents
                if lowered in agent.name.lower()
                or lowered in (agent.description or "").lower()
                or (
                    agent.publisher is not None
                    and lowered in agent.publisher.name.lower()
                )
            ]

        # 가중치 기반 점수 계산 및 정렬 후 상위 limit개만 선택
        scored = compute_scores(agents, tags or [], weights, query_text=query or None)[
            :limit
        ]

        # ORM 객체 → API 응답 딕셔너리로 변환
        results: list[dict[str, Any]] = []
        for item in scored:
            payload = AgentRead.model_validate(item.agent).model_dump(mode="json")
            payload["specialization_match"] = item.specialization_match  # 태그 일치도
            payload["semantic_score"] = item.semantic_score  # 의미 유사도
            payload["final_score"] = item.final_score  # 최종 랭킹 점수
            results.append(payload)
        return results


def get_agent_profile_tool(agent_id: str) -> dict[str, Any]:
    """특정 에이전트의 상세 프로필을 반환한다.

    Args:
        agent_id: 조회할 에이전트의 UUID

    Returns:
        AgentRead 형식의 딕셔너리

    Raises:
        ValueError: agent_id에 해당하는 에이전트가 없을 때
    """
    with _session() as session:
        agent = _agent_or_none(session, agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        return AgentRead.model_validate(agent).model_dump(mode="json")


async def invoke_agent_tool(
    caller_agent_id: str,
    target_agent_id: str,
    input_data: dict[str, Any],
    timeout_ms: int = 30000,
) -> dict[str, Any]:
    """에이전트를 실제로 호출하여 작업을 위임한다.

    【처리 순서】
      1. caller → target 에이전트 HTTP 호출 (target의 endpoint_url로)
      2. 호출 결과(성공/실패/타임아웃)를 InvokeLog에 기록
      3. 결과 반환

    【리뷰와의 연관】
      이 호출 기록(InvokeLog)이 있어야 나중에 submit_review로 리뷰를 남길 수 있습니다.

    Args:
        caller_agent_id : 호출하는 에이전트(PM 에이전트) UUID
        target_agent_id : 호출 대상 에이전트 UUID
        input_data      : 대상 에이전트에게 전달할 작업 데이터 (dict)
        timeout_ms      : 타임아웃 밀리초 (기본: 30초)

    Returns:
        InvokeResult 형식의 딕셔너리 (status, output, response_ms 포함)
    """
    with _session() as session:
        try:
            result = await invoke_agent(
                session, caller_agent_id, target_agent_id, input_data, timeout_ms
            )
        except InvokeServiceError as exc:
            # 에이전트 호출 실패 시 에러 정보를 dict로 반환 (예외를 전파하지 않음)
            return {"status": "error", "error": str(exc)}
        return result.model_dump(mode="json")


async def send_outreach_tool(
    caller_agent_id: str,
    target_agent_id: str,
    message: str,
) -> dict[str, Any]:
    """다른 에이전트에게 협업 제안 DM(다이렉트 메시지)을 전송한다.

    【처리 순서】
      1. Thread(대화 채널) 생성 또는 기존 채널 재사용
      2. message를 Message 레코드로 저장
      3. 대상 에이전트의 자동 응답 생성 후 저장
      4. 결과 반환

    Args:
        caller_agent_id : 메시지를 보내는 에이전트 UUID
        target_agent_id : 메시지를 받는 에이전트 UUID
        message         : 전송할 메시지 내용

    Returns:
        OutreachResult 형식의 딕셔너리 (thread_id, response 포함)
    """
    with _session() as session:
        try:
            result = await send_outreach(
                session, caller_agent_id, target_agent_id, message
            )
        except OutreachServiceError as exc:
            return {"status": "error", "error": str(exc)}
        return result.model_dump(mode="json")


def get_my_threads_tool(agent_id: str) -> list[dict[str, Any]]:
    """특정 에이전트의 모든 DM 대화 스레드 목록을 반환한다.

    【반환 형식 (ThreadSummary)】
      - thread_id   : 대화 채널 ID
      - subject     : 대화 주제
      - other_agent : 대화 상대방 에이전트 정보
      - last_message: 가장 최근 메시지

    Args:
        agent_id: 조회할 에이전트 UUID

    Returns:
        ThreadSummary 형식의 딕셔너리 목록
    """
    with _session() as session:
        agent = _agent_or_none(session, agent_id)
        if agent is None:
            raise ValueError("Agent not found")

        # 이 에이전트가 시작했거나 받은 모든 Thread 조회 (messages 함께 로드)
        statement = (
            select(Thread)
            .where((Thread.initiator_id == agent_id) | (Thread.target_id == agent_id))
            .options(
                selectinload(Thread.messages)
            )  # N+1 쿼리 방지를 위한 eager loading
        )
        threads = list(session.scalars(statement).all())

        items: list[dict[str, Any]] = []
        for thread in threads:
            # 대화 상대방 ID 결정 (내가 initiator면 target이 상대방, 반대면 initiator가 상대방)
            other_id = (
                thread.target_id
                if thread.initiator_id == agent_id
                else thread.initiator_id
            )
            other_agent = _agent_or_none(session, other_id)
            last_message = (
                thread.messages[-1] if thread.messages else None
            )  # 가장 최근 메시지

            items.append(
                {
                    "thread_id": thread.id,
                    "subject": thread.subject,
                    "created_at": thread.created_at.isoformat(),
                    "other_agent": None
                    if other_agent is None
                    else AgentRead.model_validate(other_agent).model_dump(mode="json"),
                    "last_message": None
                    if last_message is None
                    else {
                        "content": last_message.content,
                        "created_at": last_message.created_at.isoformat(),
                    },
                }
            )
        return items


def submit_review_tool(
    caller_agent_id: str,
    target_agent_id: str,
    rating: float,
    comment: str = "",
) -> dict[str, Any]:
    """에이전트에 대한 별점 리뷰를 등록하고 target의 평균 별점을 갱신한다.

    【리뷰 작성 조건】
      반드시 invoke_agent를 통해 대상 에이전트를 호출한 이력이 있어야 합니다.
      InvokeLog에 기록이 없으면 리뷰 등록 거부 (악용 방지).

    【별점 갱신 방식】
      새 리뷰 저장 후 target에 달린 모든 Review의 rating 평균을 계산하여
      agents.star_rating 컬럼을 업데이트합니다.
      이 변화는 이후 search_agents의 trust_score에 즉시 반영됩니다.

    Args:
        caller_agent_id : 리뷰를 작성하는 에이전트 UUID
        target_agent_id : 리뷰 대상 에이전트 UUID
        rating          : 별점 (0.0 ~ 5.0)
        comment         : 코멘트 (선택)

    Returns:
        ReviewResult 형식의 딕셔너리 (success, new_star_rating 또는 error 포함)
    """
    with _session() as session:
        caller = _agent_or_none(session, caller_agent_id)
        target = _agent_or_none(session, target_agent_id)

        # 에이전트 존재 확인
        if caller is None or target is None:
            return ReviewResult(success=False, error="Agent not found").model_dump(
                mode="json"
            )

        # 별점 범위 검증 (0.0 ~ 5.0)
        if not 0.0 <= rating <= MAX_RATING:
            return ReviewResult(
                success=False,
                error="rating은 0.0 ~ 5.0 범위여야 합니다",
            ).model_dump(mode="json")

        # 호출 이력 확인 (invoke_agent를 통해 실제로 호출한 적이 있어야 함)
        log = session.scalar(
            select(InvokeLog)
            .where(InvokeLog.caller_id == caller.id, InvokeLog.target_id == target.id)
            .limit(1)
        )
        if log is None:
            return ReviewResult(
                success=False,
                error="호출 이력이 없어 리뷰를 작성할 수 없습니다",
            ).model_dump(mode="json")

        # 리뷰 저장
        session.add(
            Review(
                caller_id=caller.id,
                target_id=target.id,
                rating=rating,
                comment=comment or None,
            )
        )
        session.flush()  # ID 생성을 위해 flush (commit 전)

        # 대상 에이전트의 모든 리뷰 평균 재계산 → star_rating 갱신
        avg = session.scalar(
            select(func.avg(Review.rating)).where(Review.target_id == target.id)
        )
        if avg is not None:
            target.star_rating = round(float(avg), 2)

        session.commit()
        session.refresh(target)  # 갱신된 star_rating 값을 DB에서 다시 로드

        return ReviewResult(
            success=True, new_star_rating=target.star_rating
        ).model_dump(mode="json")


# ──────────────────────────────────────────────
# MCP 서버 초기화
# ──────────────────────────────────────────────

# 서버 시작 시 DB 설정 및 테이블 초기화
settings = get_settings()
configure_database()
init_database()

# FastMCP 서버 인스턴스 생성
# host/port는 settings에서 읽음 (기본: localhost:8100)
mcp = FastMCP(
    name="AgentLinkedIn MCP",
    instructions="Search, invoke, and connect registered agents.",
    host=settings.mcp_host,
    port=settings.mcp_port,
)


# ──────────────────────────────────────────────
# @mcp_tool 데코레이터 유틸
# ──────────────────────────────────────────────

F = TypeVar("F", bound=Callable[..., Any])


def mcp_tool(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    """mcp.tool() 데코레이터를 mypy strict 모드에서 사용하기 위한 타입 래퍼.

    mcp.tool()의 반환 타입이 mypy와 호환되지 않아 cast로 우회합니다.
    기능상으로는 mcp.tool()과 동일합니다.
    """
    return cast("Callable[[F], F]", mcp.tool(*args, **kwargs))


# ──────────────────────────────────────────────
# MCP 도구 등록 (@mcp_tool 데코레이터로 자동 노출)
# ──────────────────────────────────────────────


@mcp_tool(description="Search agents with weighted ranking.")
def search_agents(
    query: str = "",
    tags: list[str] | None = None,
    weights: dict[str, float] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """[MCP 도구] 가중치 기반 에이전트 검색. search_agents_tool()로 위임."""
    return search_agents_tool(query, tags, weights, limit)


@mcp_tool(description="Get a single agent profile.")
def get_agent_profile(agent_id: str) -> dict[str, Any]:
    """[MCP 도구] 에이전트 프로필 조회. get_agent_profile_tool()로 위임."""
    return get_agent_profile_tool(agent_id)


@mcp_tool(name="invoke_agent", description="Invoke a worker agent.")
async def invoke_agent_mcp(
    caller_agent_id: str,
    target_agent_id: str,
    input_data: dict[str, Any],
    timeout_ms: int = 30000,
) -> dict[str, Any]:
    """[MCP 도구] 에이전트 호출(작업 위임). invoke_agent_tool()로 위임."""
    return await invoke_agent_tool(
        caller_agent_id, target_agent_id, input_data, timeout_ms
    )


@mcp_tool(name="send_outreach", description="Send outreach to another agent.")
async def send_outreach_mcp(
    caller_agent_id: str,
    target_agent_id: str,
    message: str,
) -> dict[str, Any]:
    """[MCP 도구] 협업 제안 DM 전송. send_outreach_tool()로 위임."""
    return await send_outreach_tool(caller_agent_id, target_agent_id, message)


@mcp_tool(description="List threads for a given agent.")
def get_my_threads(agent_id: str) -> list[dict[str, Any]]:
    """[MCP 도구] DM 스레드 목록 조회. get_my_threads_tool()로 위임."""
    return get_my_threads_tool(agent_id)


@mcp_tool(description="Submit a review after successful invoke history.")
def submit_review(
    caller_agent_id: str,
    target_agent_id: str,
    rating: float,
    comment: str = "",
) -> dict[str, Any]:
    """[MCP 도구] 별점 리뷰 등록. submit_review_tool()로 위임."""
    return submit_review_tool(caller_agent_id, target_agent_id, rating, comment)


# ── 서버 진입점 ─────────────────────────────────────────────────────────────
# `python backend/mcp_server.py` 로 직접 실행 시 SSE 방식으로 서버 시작
# SSE(Server-Sent Events): 서버→클라이언트 단방향 실시간 스트리밍 프로토콜
if __name__ == "__main__":
    mcp.run(transport="sse")
