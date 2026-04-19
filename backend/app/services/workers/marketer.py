"""Inline marketing worker."""

from __future__ import annotations

from typing import Any

from agents.common import chat

SYSTEM_PROMPT = (
    "You are Sujin's Marketing Agent. Focus on positioning and launch messaging."
)

FALLBACK_STRATEGY = (
    "Verified Publisher와 자율 협업 스토리를 중심으로 런칭 메시지를 설계합니다."
)
FALLBACK_CHANNELS: list[str] = ["LinkedIn", "X", "Product Hunt"]
FALLBACK_OUTREACH = "합류 가능합니다. 포지셔닝과 데모 메시지 설계를 지원하겠습니다."


async def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    brief = str(payload.get("brief", "AgentLinkedIn launch"))
    target_audience = str(payload.get("target_audience", "AI builders"))
    prompt = (
        f"Brief: {brief}\n"
        f"Target audience: {target_audience}\n"
        "Return one strategy summary and three channels."
    )
    try:
        strategy = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        strategy = FALLBACK_STRATEGY
    return {"strategy": strategy, "channels": list(FALLBACK_CHANNELS)}


async def incoming(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message", ""))
    try:
        response = await chat(SYSTEM_PROMPT, message)
    except Exception:
        response = FALLBACK_OUTREACH
    return {"response": response}
