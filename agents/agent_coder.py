"""Code worker agent."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.common import chat, print_backend_info

SYSTEM_PROMPT = (
    "You are Hyunwoo's Code Agent. Produce pragmatic architecture and code review "
    "feedback with clear action items."
)


class IncomingPayload(BaseModel):
    """Outreach message payload."""

    thread_id: str
    from_agent: dict[str, str]
    message: str


class InvokePayload(BaseModel):
    """Invoke request payload."""

    code: str = Field(default="")
    language: str = Field(default="python")


app = FastAPI(title="Code Agent")


@app.on_event("startup")
async def startup_event() -> None:
    print_backend_info()


@app.post("/incoming")
async def incoming(payload: IncomingPayload) -> dict[str, str]:
    """Respond to outreach messages."""

    prompt = (
        f"Thread: {payload.thread_id}\n"
        f"From: {payload.from_agent['name']}\n"
        f"Message: {payload.message}\n"
        "Reply as a senior engineer who can join the team."
    )
    try:
        response = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        response = (
            "합류 가능합니다. 코드 구조와 품질 게이트를 맡아 안정적으로 지원하겠습니다."
        )
    return {"response": response}


@app.post("/invoke")
async def invoke(payload: InvokePayload) -> dict[str, Any]:
    """Run a code review task."""

    prompt = (
        f"Language: {payload.language}\n"
        f"Code:\n{payload.code}\n"
        "Return one review summary and three concrete improvement suggestions."
    )
    try:
        review = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        review = "구조는 명확하지만 서비스 계층과 입출력 검증을 더 분리하면 유지보수성이 올라갑니다."
    return {
        "review": review,
        "suggestions": [
            "서비스 계층에서 외부 호출과 DB 쓰기를 분리하세요.",
            "입력 스키마 검증을 API와 MCP 양쪽에서 동일하게 유지하세요.",
            "invoke/outreach 실패 케이스를 테스트로 고정하세요.",
        ],
    }
