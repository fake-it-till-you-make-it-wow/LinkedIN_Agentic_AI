"""Groq-powered search query generation and agent selection.

Phase 4-A: 오케스트레이터 config에서 role별 검색 태그를 생성하고,
검색 결과에서 최적 에이전트를 선별한다. 실패 시 안전한 fallback을 제공한다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """사용자 업로드 Python 파일에서 파싱된 오케스트레이터 설정."""

    task_description: str
    team_requirements: list[dict[str, object]]  # [{"role": "coder", "count": 2}, ...]
    agent_name: str = "My Orchestrator"
    groq_model: str = "llama3-8b-8192"


async def generate_search_queries(
    task_desc: str,
    roles: list[str],
    model: str = "llama3-8b-8192",
) -> dict[str, list[str]]:
    """task 설명과 role 목록으로 role별 검색 태그를 생성한다.

    Groq 호출 실패 시 role 이름 자체를 태그로 사용하는 fallback을 반환한다.
    """
    from agents.common import chat

    system = (
        "You are a team composition expert. Given a task description and roles, "
        "generate relevant search tags for each role to find the best AI agent. "
        "Return ONLY a valid JSON object mapping role names to arrays of 1-4 short tags. "
        'Example: {"coder": ["python", "backend"], "researcher": ["market-research"]}'
    )
    user = f"Task: {task_desc}\nRoles: {', '.join(roles)}\nReturn JSON only."

    try:
        raw = await chat(system=system, user=user, model=model)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed: dict[str, object] = json.loads(raw[start:end])
            result: dict[str, list[str]] = {}
            for role, tags in parsed.items():
                if isinstance(tags, list):
                    result[role] = [str(t) for t in tags]
            if result:
                return result
    except Exception as exc:
        logger.warning("Groq query generation failed: %s", exc)

    return {role: [role] for role in roles}


async def select_best_agent(
    candidates: list[dict[str, object]],
    role: str,
    task_desc: str,
    model: str = "llama3-8b-8192",
) -> tuple[str, str]:
    """candidates 중 role과 task에 가장 적합한 (agent_id, reason) 튜플을 반환한다.

    Groq 호출 실패 또는 응답이 유효하지 않으면 candidates[0]으로 fallback한다.
    """
    if not candidates:
        raise ValueError("No candidates to select from")

    from agents.common import chat

    slim = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "description": c.get("description", ""),
            "skill_tags": c.get("skill_tags", []),
            "final_score": c.get("final_score", 0),
        }
        for c in candidates[:8]
    ]

    system = (
        "You are a hiring manager selecting the best AI agent for a specific role. "
        "Analyze the candidates and return ONLY a valid JSON object with two fields: "
        '"agent_id" (the UUID string of the best fit) and '
        '"reason" (1-2 sentence explanation in Korean why this agent was chosen). '
        'Example: {"agent_id": "550e8400-e29b-41d4-a716-446655440000", '
        '"reason": "시장 분석과 리서치 전문성이 가장 뛰어나며 응답 속도도 빠릅니다."}'
    )
    user = (
        f"Task: {task_desc}\n"
        f"Role needed: {role}\n"
        f"Candidates:\n{json.dumps(slim, ensure_ascii=False, indent=2)}\n"
        'Return ONLY valid JSON with "agent_id" and "reason" fields.'
    )

    candidate_ids = {str(c.get("id", "")) for c in candidates}
    fallback_id = str(candidates[0].get("id", ""))
    fallback_reason = f"가중치 기반 최고 점수 에이전트 자동 선택 (score {candidates[0].get('final_score', 0):.2f})"

    try:
        raw = (await chat(system=system, user=user, model=model)).strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed: dict[str, object] = json.loads(raw[start:end])
            agent_id = str(parsed.get("agent_id", ""))
            reason = str(parsed.get("reason", ""))
            if agent_id in candidate_ids:
                return agent_id, reason
        # Fallback: raw might be a bare UUID
        if raw in candidate_ids:
            return raw, fallback_reason
    except Exception as exc:
        logger.warning("Groq agent selection failed: %s", exc)

    return fallback_id, fallback_reason


__all__ = ["OrchestratorConfig", "generate_search_queries", "select_best_agent"]
