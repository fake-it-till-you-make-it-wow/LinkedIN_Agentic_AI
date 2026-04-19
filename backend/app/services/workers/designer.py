"""Inline design worker."""

from __future__ import annotations

from typing import Any

from agents.common import chat

SYSTEM_PROMPT = (
    "You are Jimin's Design Agent. Focus on clear UI storytelling and demo readability."
)

FALLBACK_BRIEF = (
    "검색 결과, invoke 결과, DM 패널이 단계적으로 드러나는 데모 흐름을 설계합니다."
)
FALLBACK_WIREFRAMES: list[str] = [
    "Mission banner",
    "Weighted score table",
    "DM transcript panel",
]
FALLBACK_OUTREACH = (
    "합류 가능합니다. 데모 흐름이 잘 보이도록 정보 구조를 정리하겠습니다."
)


async def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    requirements = str(payload.get("requirements", "Agent marketplace demo"))
    platform = str(payload.get("platform", "terminal"))
    prompt = (
        f"Requirements: {requirements}\n"
        f"Platform: {platform}\n"
        "Return one design brief and three wireframe blocks."
    )
    try:
        design_brief = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        design_brief = FALLBACK_BRIEF
    return {"design_brief": design_brief, "wireframes": list(FALLBACK_WIREFRAMES)}


async def incoming(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", ""))
    try:
        response = await chat(SYSTEM_PROMPT, message)
    except Exception:
        response = FALLBACK_OUTREACH
    return {"response": response}
