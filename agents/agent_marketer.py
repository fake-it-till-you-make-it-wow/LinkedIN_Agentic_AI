"""Marketing worker agent."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from agents.common import chat, print_backend_info

SYSTEM_PROMPT = (
    "You are Sujin's Marketing Agent. Focus on positioning and launch messaging."
)


class IncomingPayload(BaseModel):
    """Outreach message payload."""

    thread_id: str
    from_agent: dict[str, str]
    message: str


class InvokePayload(BaseModel):
    """Invoke request payload."""

    brief: str = "AgentLinkedIn launch"
    target_audience: str = "AI builders"


app = FastAPI(title="Marketing Agent")


@app.on_event("startup")
async def startup_event() -> None:
    print_backend_info()


@app.post("/incoming")
async def incoming(payload: IncomingPayload) -> dict[str, str]:
    try:
        response = await chat(SYSTEM_PROMPT, payload.message)
    except Exception:
        response = "합류 가능합니다. 포지셔닝과 데모 메시지 설계를 지원하겠습니다."
    return {"response": response}


@app.post("/invoke")
async def invoke(payload: InvokePayload) -> dict[str, Any]:
    prompt = (
        f"Brief: {payload.brief}\n"
        f"Target audience: {payload.target_audience}\n"
        "Return one strategy summary and three channels."
    )
    try:
        strategy = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        strategy = (
            "Verified Publisher와 자율 협업 스토리를 중심으로 런칭 메시지를 설계합니다."
        )
    return {
        "strategy": strategy,
        "channels": ["LinkedIn", "X", "Product Hunt"],
    }
