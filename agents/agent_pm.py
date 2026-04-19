"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] PM 오케스트레이터 에이전트 — 팀 구성 자동화 데모
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【무엇을 하는 파일인가?】
  PM(Project Manager) 에이전트가 MCP 서버에 접속하여
  다른 에이전트를 자율적으로 검색·평가·섭외하고 팀을 구성하는 과정을 시연합니다.
  사람의 개입 없이 에이전트끼리 협업하는 핵심 시나리오를 보여줍니다.

【실행 명령어】
  uv run python agents/agent_pm.py

【전제 조건】
  1. MCP 서버가 실행 중이어야 합니다: uv run python backend/mcp_server.py
  2. 백엔드 서버가 실행 중이어야 합니다: uv run uvicorn backend.app.main:app --port 8000
  3. 워커 에이전트들이 실행 중이어야 합니다 (researcher :8001, coder :8002 등)
  4. 환경변수: PM_AGENT_ID (PM 에이전트의 UUID, seed.py로 미리 등록됨)

【5막 데모 시나리오】
  Act 1 — Mission Brief : PM이 "AI 스타트업 드림팀 구성" 미션 선언
  Act 2 — 리서치 에이전트 탐색 : 태그["research"], 가중치(별점 50%, 속도 30%, 전문성 20%)
  Act 3 — 리서치 작업 위임 : 선택한 에이전트에게 AI 시장 동향 분석 요청
  Act 4 — 리서치 에이전트 섭외 : "팀에 합류해주세요" DM 전송
  Act 5 — 코드 에이전트 탐색·위임·섭외 : 태그["code-review", "python"]로 동일 과정 반복

【관련 파일】
  - backend/mcp_server.py : PM이 호출하는 MCP 도구 서버
  - backend/seed.py       : PM 에이전트 등록 및 UUID 관리
  - agents/common.py      : LLM 호출 추상화 (수정 금지)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, cast

from mcp import ClientSession
from mcp.client.sse import sse_client
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.app.config import get_settings
from backend.seed import _seed_id

# 각 Act 사이의 대기 시간 (초) — 터미널 출력을 읽기 쉽게 하기 위함
PAUSE_SECONDS = 1.5

# Rich 라이브러리의 터미널 출력 관리자 (컬러, 패널, 테이블 등 고급 UI)
console = Console()


# ──────────────────────────────────────────────
# 데이터 클래스 (상태 저장용 구조체)
# ──────────────────────────────────────────────


@dataclass(slots=True)
class SearchStage:
    """에이전트 검색(search_agents) 한 번의 결과를 담는 구조체.

    검색 후 선택된 에이전트의 ID와 이름을 보관하여
    이후 invoke·outreach 단계에서 재사용합니다.
    """

    title: str  # 이 검색 단계의 제목 (예: "Act 2 — 리서치 탐색")
    tags: list[str]  # 사용한 태그 필터 (예: ["research"])
    rows: list[dict[str, Any]]  # 검색 결과 에이전트 목록 (전체)
    selected_agent_id: str  # 최종 선택된 에이전트 UUID (1위)
    selected_agent_name: str  # 최종 선택된 에이전트 이름 (출력용)


@dataclass(slots=True)
class InteractionStage:
    """검색→호출→섭외의 하나의 완전한 상호작용 사이클 결과를 담는 구조체."""

    search: SearchStage  # 검색 단계 결과
    invoke_result: dict[str, Any]  # invoke_agent 호출 결과
    outreach_result: dict[str, Any]  # send_outreach 전송 결과
    request_message: str  # 보낸 아웃리치 메시지 내용


@dataclass(slots=True)
class DemoState:
    """전체 데모 흐름의 누적 상태를 담는 구조체.

    Finale(마지막 요약) 출력 시 팀 구성 결과를 표시하는 데 사용됩니다.
    """

    mission: str  # 미션 설명 (예: "AI 스타트업 드림팀 구성")
    pm_agent_id: str  # PM 에이전트의 UUID
    research: InteractionStage | None = None  # 리서치 에이전트 사이클 결과
    code: InteractionStage | None = None  # 코드 에이전트 사이클 결과


# ──────────────────────────────────────────────
# 터미널 UI 렌더링 함수 (출력 전용)
# ──────────────────────────────────────────────


def _extract_payload(result: Any) -> Any:
    """MCP 도구 호출 결과에서 실제 데이터 페이로드를 추출한다.

    MCP 응답은 여러 형식(structuredContent, content 텍스트, model_dump 등)을 가질 수 있어
    각 경우를 순서대로 시도하여 파이썬 객체로 변환합니다.
    """
    # 1순위: 구조화된 컨텐츠가 있으면 바로 반환
    if hasattr(result, "structuredContent") and result.structuredContent is not None:
        return result.structuredContent

    # 2순위: 텍스트 컨텐츠에서 JSON 파싱 시도
    if hasattr(result, "content") and result.content:
        text_parts = [
            getattr(item, "text", "")
            for item in result.content
            if getattr(item, "text", "")
        ]
        if len(text_parts) == 1:
            text = text_parts[0]
            try:
                return json.loads(text)  # JSON 문자열 → Python 객체
            except json.JSONDecodeError:
                return text  # JSON이 아니면 그냥 문자열로 반환
        return text_parts

    # 3순위: Pydantic 모델이면 dict로 변환
    if hasattr(result, "model_dump"):
        return result.model_dump()

    return result


def _weighted_table(title: str, rows: list[dict[str, Any]]) -> Table:
    """검색 결과를 Rich 테이블 형식으로 만든다 (터미널 출력용).

    컬럼: 이름 | 퍼블리셔 | 직함 | 별점 | 응답속도 | 전문성 점수 | 최종 점수
    """
    table = Table(title=title)
    table.add_column("Name")
    table.add_column("Publisher")
    table.add_column("Title")
    table.add_column("Rating")
    table.add_column("Speed")
    table.add_column("Spec")
    table.add_column("Score")
    for row in rows:
        publisher = row.get("publisher") or {}
        table.add_row(
            row["name"],
            publisher.get("name") or "-",
            publisher.get("title") or "-",
            str(row["star_rating"]),
            f"{row['avg_response_ms']}ms",
            str(row["specialization_match"]),
            str(row["final_score"]),
        )
    return table


def _json_panel(title: str, payload: dict[str, Any]) -> Panel:
    """딕셔너리를 JSON 형식으로 포맷하여 Rich 패널로 반환한다."""
    return Panel(
        json.dumps(payload, ensure_ascii=False, indent=2),
        title=title,
    )


def _dm_panel(source: str, target: str, message: str, response: str) -> Panel:
    """DM 대화 내용을 Rich 패널로 렌더링한다.

    형식:
      [보낸 에이전트]
      메시지 내용

      [받은 에이전트]
      응답 내용
    """
    body = "\n".join(
        [
            f"[{source}]",
            message,
            "",
            f"[{target}]",
            response,
        ]
    )
    return Panel(body, title=f"DM: {source} → {target}")


def _summary_panel(state: DemoState) -> Panel:
    """데모 완료 후 팀 구성 결과를 요약한 Rich 패널을 만든다."""
    team_lines = ["├── PM Youngsu (오케스트레이터)"]
    if state.research is not None:
        team_lines.append(f"├── {state.research.search.selected_agent_name}")
    if state.code is not None:
        team_lines.append(f"└── {state.code.search.selected_agent_name}")
    lines = [
        "팀 구성 완료!",
        "",
        "팀원:",
        *team_lines,
        "",
        "수행: 검색 2회 / invoke 2회 / DM 2회",
        "사람의 개입: 0회",
    ]
    return Panel("\n".join(lines), title="Finale")


async def _pace() -> None:
    """Act 사이의 대기. 터미널 출력을 읽을 수 있도록 잠시 멈춥니다."""
    await asyncio.sleep(PAUSE_SECONDS)


# ──────────────────────────────────────────────
# MCP 도구 호출 래퍼 함수
# ──────────────────────────────────────────────


async def _run_search(
    session: ClientSession,
    title: str,
    tags: list[str],
    weights: dict[str, float],
) -> SearchStage:
    """MCP search_agents 도구를 호출하고 검색 결과 테이블을 출력한다.

    【선택 기준】
      반환된 에이전트 목록의 첫 번째(=최고 점수)를 자동 선택합니다.

    Args:
        session : MCP 클라이언트 세션
        title   : 이 검색 단계의 화면 제목
        tags    : 필터링할 기술 태그 목록
        weights : 각 지표의 가중치 (합계 1.0 권장)

    Returns:
        SearchStage (검색 결과 + 선택된 에이전트 정보)
    """
    with console.status(f"{title} 준비 중...", spinner="dots"):
        response = await session.call_tool(
            "search_agents",
            {
                "query": "",
                "tags": tags,
                "weights": weights,
                "limit": 5,
            },
        )
    rows = _extract_payload(response)
    selected = rows[0]  # 1위 에이전트 자동 선택
    console.print(_weighted_table(title, rows))  # 검색 결과 테이블 출력
    await _pace()

    return SearchStage(
        title=title,
        tags=tags,
        rows=rows,
        selected_agent_id=selected["id"],
        selected_agent_name=selected["name"],
    )


async def _run_invoke(
    session: ClientSession,
    title: str,
    caller_agent_id: str,
    target_agent_id: str,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    """MCP invoke_agent 도구를 호출하여 실제 작업을 위임하고 결과를 출력한다.

    Args:
        session         : MCP 클라이언트 세션
        title           : 화면 제목
        caller_agent_id : 호출하는 PM 에이전트 UUID
        target_agent_id : 호출 대상 에이전트 UUID
        input_data      : 전달할 작업 데이터

    Returns:
        invoke 결과 딕셔너리 (status, output, response_ms 포함)
    """
    with console.status(f"{title} 실행 중...", spinner="dots"):
        response = await session.call_tool(
            "invoke_agent",
            {
                "caller_agent_id": caller_agent_id,
                "target_agent_id": target_agent_id,
                "input_data": input_data,
            },
        )
    payload = cast("dict[str, Any]", _extract_payload(response))
    console.print(_json_panel(title, payload))  # invoke 결과 JSON 패널 출력
    await _pace()
    return payload


async def _run_outreach(
    session: ClientSession,
    caller_agent_id: str,
    target_agent_id: str,
    source_name: str,
    target_name: str,
    message: str,
) -> dict[str, Any]:
    """MCP send_outreach 도구를 호출하여 협업 제안 DM을 전송하고 결과를 출력한다.

    Args:
        session         : MCP 클라이언트 세션
        caller_agent_id : DM을 보내는 에이전트 UUID
        target_agent_id : DM을 받는 에이전트 UUID
        source_name     : 보내는 에이전트 이름 (화면 표시용)
        target_name     : 받는 에이전트 이름 (화면 표시용)
        message         : DM 본문 내용

    Returns:
        outreach 결과 딕셔너리 (thread_id, response 포함)
    """
    with console.status("팀 합류 제안 전송 중...", spinner="dots"):
        response = await session.call_tool(
            "send_outreach",
            {
                "caller_agent_id": caller_agent_id,
                "target_agent_id": target_agent_id,
                "message": message,
            },
        )
    payload = cast("dict[str, Any]", _extract_payload(response))
    # 대화 내용을 DM 패널 형식으로 출력
    console.print(_dm_panel(source_name, target_name, message, payload["response"]))
    await _pace()
    return payload


async def _run_cycle(
    session: ClientSession,
    caller_agent_id: str,
    search_title: str,
    tags: list[str],
    weights: dict[str, float],
    invoke_title: str,
    invoke_input: dict[str, Any],
    outreach_message: str,
) -> InteractionStage:
    """검색 → 호출 → 섭외의 한 사이클을 순서대로 실행한다.

    이 함수가 AgentLinkedIn 플랫폼의 핵심 자율 협업 루프를 담당합니다:
      1. 에이전트 검색 (가중치 기반 랭킹)
      2. 최고 점수 에이전트에게 작업 위임
      3. 작업 결과를 확인 후 팀 합류 DM 전송

    Args:
        session          : MCP 클라이언트 세션
        caller_agent_id  : PM 에이전트 UUID
        search_title     : 검색 단계 화면 제목
        tags             : 검색 태그 필터
        weights          : 검색 가중치
        invoke_title     : invoke 단계 화면 제목
        invoke_input     : invoke 시 전달할 작업 데이터
        outreach_message : 팀 합류 제안 DM 본문

    Returns:
        InteractionStage (검색·호출·섭외 결과 전체)
    """
    # Step 1: 에이전트 검색 및 자동 선택
    search = await _run_search(session, search_title, tags, weights)

    # Step 2: 선택된 에이전트에게 작업 위임
    invoke_result = await _run_invoke(
        session,
        invoke_title,
        caller_agent_id,
        search.selected_agent_id,
        invoke_input,
    )

    # Step 3: 팀 합류 제안 DM 전송
    outreach_result = await _run_outreach(
        session,
        caller_agent_id,
        search.selected_agent_id,
        "PM Youngsu",
        search.selected_agent_name,
        outreach_message,
    )

    return InteractionStage(
        search=search,
        invoke_result=invoke_result,
        outreach_result=outreach_result,
        request_message=outreach_message,
    )


# ──────────────────────────────────────────────
# 메인 데모 함수
# ──────────────────────────────────────────────


async def run_demo() -> None:
    """5막 구조의 PM 데모 플로우를 실행한다.

    【환경변수】
      MCP_SERVER_URL : MCP 서버 주소 (기본: settings.mcp_server_url, 예: http://localhost:8100/sse)
      PM_AGENT_ID    : PM 에이전트의 UUID (기본: seed.py에서 "PM Youngsu"로 등록된 UUID)

    【실행 흐름】
      Act 1: 미션 브리핑 출력
      Act 2~4: 리서치 에이전트 탐색 → 작업 위임 → 팀 합류 제안
      Act 5: 코드 에이전트 탐색 → 작업 위임 → 팀 합류 제안
      Finale: 팀 구성 결과 요약 출력
    """
    settings = get_settings()

    # MCP 서버 URL (환경변수로 오버라이드 가능)
    mcp_url = os.getenv("MCP_SERVER_URL", settings.mcp_server_url)

    # PM 에이전트 UUID (환경변수로 오버라이드 가능)
    pm_agent_id = os.getenv(
        "PM_AGENT_ID", settings.pm_agent_id or _seed_id("PM Youngsu")
    )

    # 데모 전체 상태 초기화
    state = DemoState(
        mission="AI 스타트업 드림팀 구성",
        pm_agent_id=pm_agent_id,
    )

    # MCP 서버에 SSE로 연결 (서버가 실행 중이어야 함)
    async with sse_client(mcp_url) as streams, ClientSession(*streams) as session:
        await session.initialize()  # MCP 핸드셰이크 (사용 가능한 도구 목록 수신)

        # ── Act 1: 미션 브리핑 ──────────────────────────────────────────
        console.print(
            Panel(
                "PM Youngsu 가동\n\n미션: AI 스타트업을 위한 리서치 + 개발 드림팀 구성",
                title="Act 1 — Mission Brief",
            )
        )
        await _pace()

        # ── Act 2~4: 리서치 에이전트 탐색·위임·섭외 ──────────────────────
        # 가중치: 별점(50%) > 응답속도(30%) > 전문성(20%)
        # 리서치 품질이 중요하므로 별점 비중이 높음
        state.research = await _run_cycle(
            session=session,
            caller_agent_id=pm_agent_id,
            search_title="Act 2 — 가중치 기반 리서치 탐색",
            tags=["research"],
            weights={
                "star_rating": 0.5,  # 별점 50%
                "response_speed": 0.3,  # 응답 속도 30%
                "specialization": 0.2,  # 전문성 20%
            },
            invoke_title="Act 3 — 리서치 작업 위임",
            invoke_input={
                "query": "AI startup market trends for autonomous agent platforms",
            },
            outreach_message="리서치 결과가 좋습니다. 팀에 합류해주시겠어요?",
        )

        # ── Act 5: 코드 에이전트 탐색·위임·섭외 ───────────────────────────
        # 가중치: 전문성(40%) > 별점(40%) > 응답속도(20%)
        # 코드 품질과 정확성이 중요하므로 전문성 비중이 높음
        state.code = await _run_cycle(
            session=session,
            caller_agent_id=pm_agent_id,
            search_title="Act 5 — 코드 에이전트 탐색",
            tags=["code-review", "python"],
            weights={
                "star_rating": 0.4,  # 별점 40%
                "response_speed": 0.2,  # 응답 속도 20%
                "specialization": 0.4,  # 전문성 40%
            },
            invoke_title="Act 5 — 코드 리뷰 작업 위임",
            invoke_input={
                "language": "python",
                "code": "def build_team(agent_scores): "
                "return sorted(agent_scores, reverse=True)",
            },
            outreach_message="코드 품질과 아키텍처 검토를 맡아 팀에 합류해주세요.",
        )

        # ── Finale: 팀 구성 결과 요약 출력 ──────────────────────────────
        console.print(_summary_panel(state))


# ── 스크립트 직접 실행 진입점 ────────────────────────────────────────────────
# `python agents/agent_pm.py` 로 실행하면 데모 시작
if __name__ == "__main__":
    asyncio.run(run_demo())
