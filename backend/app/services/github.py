"""GitHub webhook payload handlers (Phase 3-B).

서명 검증은 PoC 범위 밖 — `X-Hub-Signature-256` HMAC 비교는 Phase 4에서 도입.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Agent, AgentRelease, new_uuid


class GitHubWebhookError(Exception):
    """Raised when a GitHub webhook payload cannot be processed."""


def _agent_by_repo(session: Session, full_name: str) -> Agent | None:
    return session.scalar(select(Agent).where(Agent.github_repo == full_name))


def _parse_iso(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(UTC)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def handle_release_event(
    session: Session, payload: dict[str, Any]
) -> dict[str, Any]:
    """Insert or update an AgentRelease row for a GitHub release webhook."""

    action = payload.get("action")
    if action not in {"published", "released", "created"}:
        return {"status": "ignored", "reason": f"action={action}"}

    repo = cast("dict[str, Any]", payload.get("repository") or {})
    release = cast("dict[str, Any]", payload.get("release") or {})
    full_name = cast("str | None", repo.get("full_name"))
    tag = cast("str | None", release.get("tag_name"))
    if not full_name or not tag:
        raise GitHubWebhookError("repository.full_name과 release.tag_name이 필요합니다")

    agent = _agent_by_repo(session, full_name)
    if agent is None:
        return {"status": "ignored", "reason": "no matching agent"}

    existing = session.scalar(
        select(AgentRelease).where(
            AgentRelease.agent_id == agent.id, AgentRelease.tag == tag
        )
    )
    published_at = _parse_iso(
        cast("str | None", release.get("published_at") or release.get("created_at"))
    )
    if existing is None:
        session.add(
            AgentRelease(
                id=new_uuid(),
                agent_id=agent.id,
                tag=tag,
                name=cast("str | None", release.get("name")),
                body=cast("str | None", release.get("body")),
                published_at=published_at,
            )
        )
    else:
        existing.name = cast("str | None", release.get("name", existing.name))
        existing.body = cast("str | None", release.get("body", existing.body))
        existing.published_at = published_at
    session.commit()
    return {"status": "ok", "agent_id": agent.id, "tag": tag}


def handle_star_event(
    session: Session, payload: dict[str, Any]
) -> dict[str, Any]:
    """Adjust an agent's github_star_count based on a star webhook."""

    action = payload.get("action")
    repo = cast("dict[str, Any]", payload.get("repository") or {})
    full_name = cast("str | None", repo.get("full_name"))
    if not full_name:
        raise GitHubWebhookError("repository.full_name이 필요합니다")

    agent = _agent_by_repo(session, full_name)
    if agent is None:
        return {"status": "ignored", "reason": "no matching agent"}

    authoritative = repo.get("stargazers_count")
    if isinstance(authoritative, int):
        agent.github_star_count = max(0, authoritative)
    elif action == "created":
        agent.github_star_count += 1
    elif action == "deleted":
        agent.github_star_count = max(0, agent.github_star_count - 1)
    else:
        return {"status": "ignored", "reason": f"action={action}"}

    session.commit()
    return {
        "status": "ok",
        "agent_id": agent.id,
        "star_count": agent.github_star_count,
    }
