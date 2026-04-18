"""FastMCP server exposing AgentLinkedIn tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.config import get_settings
from backend.app.database import configure_database, get_session_factory, init_database
from backend.app.models import Agent, InvokeLog, Thread
from backend.app.schemas import AgentRead, ReviewResult
from backend.app.services.invoke import InvokeServiceError, invoke_agent
from backend.app.services.outreach import OutreachServiceError, send_outreach
from backend.app.services.scoring import compute_scores

MAX_RATING = 5.0


def _session() -> Session:
    return get_session_factory()()


def _agent_or_none(session: Session, agent_id: str) -> Agent | None:
    return session.get(Agent, agent_id)


def search_agents_tool(
    query: str = "",
    tags: list[str] | None = None,
    weights: dict[str, float] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search agents with weighted scoring."""

    with _session() as session:
        agents = list(session.scalars(select(Agent)).all())
        if query:
            lowered = query.lower()
            agents = [
                agent
                for agent in agents
                if lowered in agent.name.lower()
                or lowered in (agent.description or "").lower()
                or lowered in (agent.publisher_name or "").lower()
            ]
        scored = compute_scores(agents, tags or [], weights)[:limit]
        results: list[dict[str, Any]] = []
        for item in scored:
            payload = AgentRead.model_validate(item.agent).model_dump(mode="json")
            payload["specialization_match"] = item.specialization_match
            payload["final_score"] = item.final_score
            results.append(payload)
        return results


def get_agent_profile_tool(agent_id: str) -> dict[str, Any]:
    """Get one agent profile."""

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
    """Invoke a worker agent."""

    with _session() as session:
        try:
            result = await invoke_agent(
                session, caller_agent_id, target_agent_id, input_data, timeout_ms
            )
        except InvokeServiceError as exc:
            return {"status": "error", "error": str(exc)}
        return result.model_dump(mode="json")


async def send_outreach_tool(
    caller_agent_id: str,
    target_agent_id: str,
    message: str,
) -> dict[str, Any]:
    """Send an outreach message to another agent."""

    with _session() as session:
        try:
            result = await send_outreach(
                session, caller_agent_id, target_agent_id, message
            )
        except OutreachServiceError as exc:
            return {"status": "error", "error": str(exc)}
        return result.model_dump(mode="json")


def get_my_threads_tool(agent_id: str) -> list[dict[str, Any]]:
    """List thread summaries for an agent."""

    with _session() as session:
        agent = _agent_or_none(session, agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        statement = (
            select(Thread)
            .where((Thread.initiator_id == agent_id) | (Thread.target_id == agent_id))
            .options(selectinload(Thread.messages))
        )
        threads = list(session.scalars(statement).all())
        items: list[dict[str, Any]] = []
        for thread in threads:
            other_id = (
                thread.target_id
                if thread.initiator_id == agent_id
                else thread.initiator_id
            )
            other_agent = _agent_or_none(session, other_id)
            last_message = thread.messages[-1] if thread.messages else None
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
    """Update an agent rating after validating invoke history."""

    del comment
    with _session() as session:
        caller = _agent_or_none(session, caller_agent_id)
        target = _agent_or_none(session, target_agent_id)
        if caller is None or target is None:
            return ReviewResult(success=False, error="Agent not found").model_dump(
                mode="json"
            )
        if not 0.0 <= rating <= MAX_RATING:
            return ReviewResult(
                success=False,
                error="rating은 0.0 ~ 5.0 범위여야 합니다",
            ).model_dump(mode="json")
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

        target.star_rating = round((target.star_rating + rating) / 2, 2)
        session.commit()
        session.refresh(target)
        return ReviewResult(
            success=True, new_star_rating=target.star_rating
        ).model_dump(mode="json")


settings = get_settings()
configure_database()
init_database()
mcp = FastMCP(
    name="AgentLinkedIn MCP",
    instructions="Search, invoke, and connect registered agents.",
    host=settings.mcp_host,
    port=settings.mcp_port,
)


F = TypeVar("F", bound=Callable[..., Any])


def mcp_tool(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    """Typed wrapper around `mcp.tool()` to satisfy mypy strict mode."""

    return cast("Callable[[F], F]", mcp.tool(*args, **kwargs))


@mcp_tool(description="Search agents with weighted ranking.")
def search_agents(
    query: str = "",
    tags: list[str] | None = None,
    weights: dict[str, float] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    return search_agents_tool(query, tags, weights, limit)


@mcp_tool(description="Get a single agent profile.")
def get_agent_profile(agent_id: str) -> dict[str, Any]:
    return get_agent_profile_tool(agent_id)


@mcp_tool(name="invoke_agent", description="Invoke a worker agent.")
async def invoke_agent_mcp(
    caller_agent_id: str,
    target_agent_id: str,
    input_data: dict[str, Any],
    timeout_ms: int = 30000,
) -> dict[str, Any]:
    return await invoke_agent_tool(
        caller_agent_id, target_agent_id, input_data, timeout_ms
    )


@mcp_tool(name="send_outreach", description="Send outreach to another agent.")
async def send_outreach_mcp(
    caller_agent_id: str,
    target_agent_id: str,
    message: str,
) -> dict[str, Any]:
    return await send_outreach_tool(caller_agent_id, target_agent_id, message)


@mcp_tool(description="List threads for a given agent.")
def get_my_threads(agent_id: str) -> list[dict[str, Any]]:
    return get_my_threads_tool(agent_id)


@mcp_tool(description="Submit a review after successful invoke history.")
def submit_review(
    caller_agent_id: str,
    target_agent_id: str,
    rating: float,
    comment: str = "",
) -> dict[str, Any]:
    return submit_review_tool(caller_agent_id, target_agent_id, rating, comment)


if __name__ == "__main__":
    mcp.run(transport="sse")
