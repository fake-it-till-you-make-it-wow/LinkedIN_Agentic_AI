"""PM demo orchestrator using the MCP server."""

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

PAUSE_SECONDS = 1.5
console = Console()


@dataclass(slots=True)
class SearchStage:
    """Captured result of one search stage."""

    title: str
    tags: list[str]
    rows: list[dict[str, Any]]
    selected_agent_id: str
    selected_agent_name: str


@dataclass(slots=True)
class InteractionStage:
    """Captured result of one invoke/outreach cycle."""

    search: SearchStage
    invoke_result: dict[str, Any]
    outreach_result: dict[str, Any]
    request_message: str


@dataclass(slots=True)
class DemoState:
    """Aggregated demo state for final summary."""

    mission: str
    pm_agent_id: str
    research: InteractionStage | None = None
    code: InteractionStage | None = None


def _extract_payload(result: Any) -> Any:
    if hasattr(result, "structuredContent") and result.structuredContent is not None:
        return result.structuredContent
    if hasattr(result, "content") and result.content:
        text_parts = [
            getattr(item, "text", "")
            for item in result.content
            if getattr(item, "text", "")
        ]
        if len(text_parts) == 1:
            text = text_parts[0]
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return text_parts
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


def _weighted_table(title: str, rows: list[dict[str, Any]]) -> Table:
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
    return Panel(
        json.dumps(payload, ensure_ascii=False, indent=2),
        title=title,
    )


def _dm_panel(source: str, target: str, message: str, response: str) -> Panel:
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
    await asyncio.sleep(PAUSE_SECONDS)


async def _run_search(
    session: ClientSession,
    title: str,
    tags: list[str],
    weights: dict[str, float],
) -> SearchStage:
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
    selected = rows[0]
    console.print(_weighted_table(title, rows))
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
    console.print(_json_panel(title, payload))
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
    search = await _run_search(session, search_title, tags, weights)
    invoke_result = await _run_invoke(
        session,
        invoke_title,
        caller_agent_id,
        search.selected_agent_id,
        invoke_input,
    )
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


async def run_demo() -> None:
    """Run the 5-act PM demo flow."""

    settings = get_settings()
    mcp_url = os.getenv("MCP_SERVER_URL", settings.mcp_server_url)
    pm_agent_id = os.getenv(
        "PM_AGENT_ID", settings.pm_agent_id or _seed_id("PM Youngsu")
    )
    state = DemoState(
        mission="AI 스타트업 드림팀 구성",
        pm_agent_id=pm_agent_id,
    )

    async with sse_client(mcp_url) as streams, ClientSession(*streams) as session:
        await session.initialize()

        console.print(
            Panel(
                "PM Youngsu 가동\n\n미션: AI 스타트업을 위한 리서치 + 개발 드림팀 구성",
                title="Act 1 — Mission Brief",
            )
        )
        await _pace()

        state.research = await _run_cycle(
            session=session,
            caller_agent_id=pm_agent_id,
            search_title="Act 2 — 가중치 기반 리서치 탐색",
            tags=["research"],
            weights={
                "star_rating": 0.5,
                "response_speed": 0.3,
                "specialization": 0.2,
            },
            invoke_title="Act 3 — 리서치 작업 위임",
            invoke_input={
                "query": "AI startup market trends for autonomous agent platforms",
            },
            outreach_message="리서치 결과가 좋습니다. 팀에 합류해주시겠어요?",
        )

        state.code = await _run_cycle(
            session=session,
            caller_agent_id=pm_agent_id,
            search_title="Act 5 — 코드 에이전트 탐색",
            tags=["code-review", "python"],
            weights={
                "star_rating": 0.4,
                "response_speed": 0.2,
                "specialization": 0.4,
            },
            invoke_title="Act 5 — 코드 리뷰 작업 위임",
            invoke_input={
                "language": "python",
                "code": "def build_team(agent_scores): "
                "return sorted(agent_scores, reverse=True)",
            },
            outreach_message="코드 품질과 아키텍처 검토를 맡아 팀에 합류해주세요.",
        )

        console.print(_summary_panel(state))


if __name__ == "__main__":
    asyncio.run(run_demo())
