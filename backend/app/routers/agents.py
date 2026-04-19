"""Agent-related REST routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.database import get_db_session
from backend.app.models import Agent, Message, Publisher, Thread
from backend.app.schemas import (
    AgentCreate,
    AgentRead,
    AgentStats,
    AgentUpdate,
    MessageRead,
    SearchAgentResult,
    SearchWeights,
    ThreadSummary,
)
from backend.app.services.observability import compute_agent_stats
from backend.app.services.scoring import compute_scores

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_agent_or_404(session: Session, agent_id: str) -> Agent:
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found"
        )
    return agent


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate, session: Session = Depends(get_db_session)
) -> Agent:
    """Create an agent profile."""

    agent = Agent(**payload.model_dump())
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("", response_model=list[AgentRead])
def list_agents(session: Session = Depends(get_db_session)) -> list[Agent]:
    """Return all registered agents."""

    return list(session.scalars(select(Agent).order_by(Agent.created_at)).all())


@router.get("/search", response_model=list[SearchAgentResult])
def search_agents(
    q: str = "",
    tags: str = "",
    weights: str = "",
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_db_session),
) -> list[SearchAgentResult]:
    """Search agents and rank them by weighted score."""

    statement = select(Agent)
    if q:
        statement = statement.outerjoin(Publisher, Agent.publisher_id == Publisher.id)
        statement = statement.where(
            or_(
                Agent.name.ilike(f"%{q}%"),
                Agent.description.ilike(f"%{q}%"),
                Publisher.name.ilike(f"%{q}%"),
            )
        )
    agents = list(session.scalars(statement).all())
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    parsed_weights = SearchWeights().model_dump()
    if weights:
        parsed_weights = SearchWeights.model_validate(json.loads(weights)).model_dump()
    scored = compute_scores(
        agents, tag_list, parsed_weights, query_text=q or None
    )[:limit]

    results: list[SearchAgentResult] = []
    for item in scored:
        data = AgentRead.model_validate(item.agent).model_dump()
        results.append(
            SearchAgentResult(
                **data,
                specialization_match=item.specialization_match,
                semantic_score=item.semantic_score,
                final_score=item.final_score,
            )
        )
    return results


@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: str, session: Session = Depends(get_db_session)) -> Agent:
    """Return a single agent profile."""

    return _get_agent_or_404(session, agent_id)


@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    session: Session = Depends(get_db_session),
) -> Agent:
    """Partially update an agent profile."""

    agent = _get_agent_or_404(session, agent_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/{agent_id}/stats", response_model=AgentStats)
def get_agent_stats(
    agent_id: str, session: Session = Depends(get_db_session)
) -> AgentStats:
    """Return operational metrics + status flag for an agent."""

    agent = _get_agent_or_404(session, agent_id)
    return compute_agent_stats(session, agent)


@router.get("/{agent_id}/threads", response_model=list[ThreadSummary])
def get_agent_threads(
    agent_id: str, session: Session = Depends(get_db_session)
) -> list[ThreadSummary]:
    """Return thread summaries for a given agent."""

    agent = _get_agent_or_404(session, agent_id)
    statement = select(Thread).where(
        or_(Thread.initiator_id == agent.id, Thread.target_id == agent.id)
    )
    threads = list(session.scalars(statement).all())
    summaries: list[ThreadSummary] = []
    for thread in threads:
        other_id = (
            thread.target_id if thread.initiator_id == agent.id else thread.initiator_id
        )
        other_agent = _get_agent_or_404(session, other_id)
        last_message = session.scalar(
            select(Message)
            .where(Message.thread_id == thread.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        summaries.append(
            ThreadSummary(
                thread_id=thread.id,
                subject=thread.subject,
                created_at=thread.created_at,
                other_agent=AgentRead.model_validate(other_agent),
                last_message=None
                if last_message is None
                else MessageRead.model_validate(last_message),
            )
        )
    return summaries
