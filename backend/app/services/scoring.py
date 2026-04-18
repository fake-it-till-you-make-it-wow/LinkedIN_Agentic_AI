"""Weighted agent scoring utilities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.models import Agent

DEFAULT_WEIGHTS: dict[str, float] = {
    "star_rating": 0.4,
    "success_rate": 0.3,
    "response_speed": 0.2,
    "specialization": 0.1,
}


@dataclass(slots=True)
class ScoredAgent:
    """Scored representation of an agent."""

    agent: Agent
    specialization_match: float
    final_score: float


def compute_scores(
    agents: Sequence[Agent],
    query_tags: Sequence[str],
    weights: dict[str, float] | None = None,
) -> list[ScoredAgent]:
    """Score and sort agents for search results."""

    effective_weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    requested_tags = {tag.strip().lower() for tag in query_tags if tag.strip()}
    results: list[ScoredAgent] = []

    for agent in agents:
        agent_tags = {tag.lower() for tag in (agent.skill_tags or [])}
        tag_match = agent_tags & requested_tags
        specialization = len(tag_match) / max(len(requested_tags), 1)
        speed = 1 - min(agent.avg_response_ms / 5000, 1.0)
        score = (
            effective_weights["star_rating"] * (agent.star_rating / 5)
            + effective_weights["success_rate"] * agent.success_rate
            + effective_weights["response_speed"] * speed
            + effective_weights["specialization"] * specialization
        )
        results.append(
            ScoredAgent(
                agent=agent,
                specialization_match=round(specialization, 4),
                final_score=round(score, 4),
            )
        )

    return sorted(results, key=lambda item: item.final_score, reverse=True)
