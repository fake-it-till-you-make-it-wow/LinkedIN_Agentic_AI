"""Operational observability aggregates (Phase 2.1)."""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.app.models import Agent, InvokeLog, Publisher, Review
from backend.app.schemas import AdminHealth, AgentStats

HEALTHY_ERROR_THRESHOLD = 0.1
DEGRADED_ERROR_THRESHOLD = 0.3


def _agent_status(total: int, error_rate: float) -> str:
    if total == 0:
        return "idle"
    if error_rate < HEALTHY_ERROR_THRESHOLD:
        return "healthy"
    if error_rate < DEGRADED_ERROR_THRESHOLD:
        return "degraded"
    return "failing"


def compute_agent_stats(session: Session, agent: Agent) -> AgentStats:
    """Aggregate InvokeLog + Review metrics for a single agent."""

    total, successes, errors, timeouts, last_invoked_at = session.execute(
        select(
            func.count(InvokeLog.id),
            func.sum(case((InvokeLog.status == "success", 1), else_=0)),
            func.sum(case((InvokeLog.status == "error", 1), else_=0)),
            func.sum(case((InvokeLog.status == "timeout", 1), else_=0)),
            func.max(InvokeLog.created_at),
        ).where(InvokeLog.target_id == agent.id)
    ).one()

    success_count = int(successes or 0)
    error_count = int(errors or 0)
    timeout_count = int(timeouts or 0)

    avg_ms = session.scalar(
        select(func.avg(InvokeLog.response_ms)).where(
            InvokeLog.target_id == agent.id,
            InvokeLog.status == "success",
        )
    )

    review_count = session.scalar(
        select(func.count(Review.id)).where(Review.target_id == agent.id)
    ) or 0

    success_rate = success_count / total if total else 0.0
    error_rate = (error_count + timeout_count) / total if total else 0.0

    return AgentStats(
        agent_id=agent.id,
        total_invocations=total,
        success_count=success_count,
        error_count=error_count,
        timeout_count=timeout_count,
        success_rate=round(success_rate, 4),
        avg_response_ms=int(avg_ms) if avg_ms is not None else None,
        review_count=int(review_count),
        star_rating=agent.star_rating,
        last_invoked_at=last_invoked_at,
        status=_agent_status(total, error_rate),
    )


def compute_admin_health(session: Session) -> AdminHealth:
    """Aggregate system-level counters for the operator dashboard."""

    agents_total = session.scalar(select(func.count(Agent.id))) or 0
    agents_verified = (
        session.scalar(select(func.count(Agent.id)).where(Agent.verified.is_(True)))
        or 0
    )
    publishers_total = session.scalar(select(func.count(Publisher.id))) or 0
    publishers_verified = (
        session.scalar(
            select(func.count(Publisher.id)).where(Publisher.verified.is_(True))
        )
        or 0
    )
    reviews_total = session.scalar(select(func.count(Review.id))) or 0

    invocations_total, failures = session.execute(
        select(
            func.count(InvokeLog.id),
            func.sum(
                case((InvokeLog.status.in_(("error", "timeout")), 1), else_=0)
            ),
        )
    ).one()
    invocations_total = int(invocations_total or 0)
    error_rate = (
        (int(failures or 0) / invocations_total) if invocations_total else 0.0
    )

    if invocations_total == 0:
        status = "idle"
    elif error_rate < HEALTHY_ERROR_THRESHOLD:
        status = "healthy"
    elif error_rate < DEGRADED_ERROR_THRESHOLD:
        status = "degraded"
    else:
        status = "failing"

    return AdminHealth(
        agents_total=int(agents_total),
        agents_verified=int(agents_verified),
        publishers_total=int(publishers_total),
        publishers_verified=int(publishers_verified),
        invocations_total=invocations_total,
        invocation_error_rate=round(error_rate, 4),
        reviews_total=int(reviews_total),
        status=status,
    )
