"""Weighted agent scoring utilities."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.models import Agent
from backend.app.services.semantic import compute_semantic_scores

DEFAULT_WEIGHTS: dict[str, float] = {
    "star_rating": 0.35,
    "success_rate": 0.25,
    "response_speed": 0.2,
    "specialization": 0.1,
    "semantic": 0.1,
}


@dataclass(slots=True)
class ScoredAgent:
    """Scored representation of an agent."""

    agent: Agent
    specialization_match: float
    semantic_score: float
    final_score: float


def compute_scores(
    agents: Sequence[Agent],
    query_tags: Sequence[str],
    weights: dict[str, float] | None = None,
    query_text: str | None = None,
) -> list[ScoredAgent]:
    """Score and sort agents for search results."""

    effective_weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    requested_tags = {tag.strip().lower() for tag in query_tags if tag.strip()}
    semantic_scores: dict[str, float] = {}
    if query_text and query_text.strip():
        semantic_scores = compute_semantic_scores(agents, query_text)

    results: list[ScoredAgent] = []

    for agent in agents:
        agent_tags = {tag.lower() for tag in (agent.skill_tags or [])}
        tag_match = agent_tags & requested_tags
        specialization = len(tag_match) / max(len(requested_tags), 1)
        speed = 1 - min(agent.avg_response_ms / 5000, 1.0)
        semantic = semantic_scores.get(agent.id, 0.0)
        score = (
            effective_weights["star_rating"] * (agent.star_rating / 5)
            + effective_weights["success_rate"] * agent.success_rate
            + effective_weights["response_speed"] * speed
            + effective_weights["specialization"] * specialization
            + effective_weights.get("semantic", 0.0) * semantic
        )
        results.append(
            ScoredAgent(
                agent=agent,
                specialization_match=round(specialization, 4),
                semantic_score=round(semantic, 4),
                final_score=round(score, 4),
            )
        )

    return sorted(results, key=lambda item: item.final_score, reverse=True)
