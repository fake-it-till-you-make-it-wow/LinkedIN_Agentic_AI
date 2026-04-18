"""Design worker agent."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from agents.common import chat, print_backend_info

SYSTEM_PROMPT = (
    "You are Jimin's Design Agent. Focus on clear UI storytelling and demo readability."
)


class IncomingPayload(BaseModel):
    """Outreach message payload."""

    thread_id: str
    from_agent: dict[str, str]
    message: str


class InvokePayload(BaseModel):
    """Invoke request payload."""

    requirements: str = "Agent marketplace demo"
    platform: str = "terminal"


app = FastAPI(title="Design Agent")


@app.on_event("startup")
async def startup_event() -> None:
    print_backend_info()


@app.post("/incoming")
async def incoming(payload: IncomingPayload) -> dict[str, str]:
    try:
        response = await chat(SYSTEM_PROMPT, payload.message)
    except Exception:
        response = (
            "합류 가능합니다. 데모 흐름이 잘 보이도록 정보 구조를 정리하겠습니다."
        )
    return {"response": response}


@app.post("/invoke")
async def invoke(payload: InvokePayload) -> dict[str, Any]:
    prompt = (
        f"Requirements: {payload.requirements}\n"
        f"Platform: {payload.platform}\n"
        "Return one design brief and three wireframe blocks."
    )
    try:
        design_brief = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        design_brief = "검색 결과, invoke 결과, DM 패널이 단계적으로 드러나는 데모 흐름을 설계합니다."
    return {
        "design_brief": design_brief,
        "wireframes": [
            "Mission banner",
            "Weighted score table",
            "DM transcript panel",
        ],
    }
