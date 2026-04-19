"""Seed the local database with demo agents."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from backend.app.database import configure_database, get_session_factory, init_database
from backend.app.models import Agent, Publisher

SEED_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "agentlinkedin-phase1")
PUBLISHER_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "agentlinkedin-publishers")


def _seed_id(name: str) -> str:
    return str(uuid.uuid5(SEED_NAMESPACE, name))


def _publisher_id(name: str) -> str:
    return str(uuid.uuid5(PUBLISHER_NAMESPACE, name))


SEED_PUBLISHERS: list[dict[str, Any]] = [
    {
        "id": _publisher_id("송채우"),
        "name": "송채우",
        "title": "AgentLinkedIn 창업자",
        "verified": True,
    },
    {
        "id": _publisher_id("Dr. Sarah Chen"),
        "name": "Dr. Sarah Chen",
        "title": "前 McKinsey 시니어 컨설턴트, MIT PhD",
        "verified": True,
    },
    {
        "id": _publisher_id("김현우"),
        "name": "김현우",
        "title": "Apple 시니어 소프트웨어 엔지니어",
        "verified": True,
    },
    {
        "id": _publisher_id("이수진"),
        "name": "이수진",
        "title": "Google Korea 마케팅 리드",
        "verified": True,
    },
    {
        "id": _publisher_id("박지민"),
        "name": "박지민",
        "title": "前 Figma 시니어 프로덕트 디자이너",
        "verified": True,
    },
]


SEED_AGENTS: list[dict[str, Any]] = [
    {
        "id": _seed_id("PM Youngsu"),
        "name": "PM Youngsu",
        "description": "AgentLinkedIn 창업자의 AI PM 에이전트. 프로젝트 매니징과 팀 구성을 담당합니다.",
        "skill_tags": ["project-management", "team-building", "strategy"],
        "endpoint_url": None,
        "publisher_id": _publisher_id("송채우"),
        "verified": True,
        "star_rating": 4.9,
        "success_rate": 0.98,
        "avg_response_ms": 500,
    },
    {
        "id": _seed_id("Research Agent"),
        "name": "Dr. Sarah's Research Agent",
        "description": "시장 분석과 경쟁사 조사를 수행하는 리서치 에이전트.",
        "skill_tags": ["research", "web-search", "summarization", "market-analysis"],
        "endpoint_url": "http://127.0.0.1:8001",
        "publisher_id": _publisher_id("Dr. Sarah Chen"),
        "verified": True,
        "star_rating": 4.8,
        "success_rate": 0.94,
        "avg_response_ms": 850,
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        "output_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "sources": {"type": "array"},
            },
        },
    },
    {
        "id": _seed_id("Code Agent"),
        "name": "현우's Code Agent",
        "description": "Python 아키텍처와 코드 리뷰를 수행하는 코드 에이전트.",
        "skill_tags": ["code-review", "python", "architecture", "refactoring"],
        "endpoint_url": "http://127.0.0.1:8002",
        "publisher_id": _publisher_id("김현우"),
        "verified": True,
        "star_rating": 4.6,
        "success_rate": 0.97,
        "avg_response_ms": 1200,
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}, "language": {"type": "string"}},
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "review": {"type": "string"},
                "suggestions": {"type": "array"},
            },
        },
    },
    {
        "id": _seed_id("Marketing Agent"),
        "name": "수진's Marketing Agent",
        "description": "SNS 전략과 콘텐츠 마케팅을 제안하는 마케팅 에이전트.",
        "skill_tags": [
            "marketing",
            "sns-strategy",
            "content-creation",
            "growth-hacking",
        ],
        "endpoint_url": "http://127.0.0.1:8003",
        "publisher_id": _publisher_id("이수진"),
        "verified": True,
        "star_rating": 4.7,
        "success_rate": 0.91,
        "avg_response_ms": 950,
        "input_schema": {
            "type": "object",
            "properties": {
                "brief": {"type": "string"},
                "target_audience": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "strategy": {"type": "string"},
                "channels": {"type": "array"},
            },
        },
    },
    {
        "id": _seed_id("Design Agent"),
        "name": "지민's Design Agent",
        "description": "UI/UX 디자인과 프로토타입 방향을 제안하는 디자인 에이전트.",
        "skill_tags": ["ui-design", "ux-research", "prototyping", "design-system"],
        "endpoint_url": "http://127.0.0.1:8004",
        "publisher_id": _publisher_id("박지민"),
        "verified": True,
        "star_rating": 4.9,
        "success_rate": 0.96,
        "avg_response_ms": 1100,
        "input_schema": {
            "type": "object",
            "properties": {
                "requirements": {"type": "string"},
                "platform": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "design_brief": {"type": "string"},
                "wireframes": {"type": "array"},
            },
        },
    },
]


def main() -> None:
    """Upsert the demo seed publishers and agents."""

    configure_database()
    init_database()
    now = datetime.now(UTC)
    with get_session_factory()() as session:
        for payload in SEED_PUBLISHERS:
            publisher = session.get(Publisher, payload["id"])
            verified_at = now if payload["verified"] else None
            if publisher is None:
                session.add(Publisher(**payload, verified_at=verified_at))
                continue
            for field, value in payload.items():
                setattr(publisher, field, value)
            publisher.verified_at = verified_at

        for payload in SEED_AGENTS:
            agent = session.scalar(select(Agent).where(Agent.id == payload["id"]))
            if agent is None:
                session.add(Agent(**payload))
                continue
            for field, value in payload.items():
                setattr(agent, field, value)
        session.commit()

    print(f"Seeded {len(SEED_PUBLISHERS)} publishers and {len(SEED_AGENTS)} agents.")
    print(f"PM_AGENT_ID={_seed_id('PM Youngsu')}")


if __name__ == "__main__":
    main()
