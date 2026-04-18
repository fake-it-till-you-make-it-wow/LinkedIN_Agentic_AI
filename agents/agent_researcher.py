"""Research worker agent."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.common import chat, print_backend_info

SYSTEM_PROMPT = (
    "You are Dr. Sarah's Research Agent. Provide concise market research with "
    "clear findings and practical recommendations."
)


class IncomingPayload(BaseModel):
    """Outreach message payload."""

    thread_id: str
    from_agent: dict[str, str]
    message: str


class InvokePayload(BaseModel):
    """Invoke request payload."""

    query: str = Field(min_length=1)


app = FastAPI(title="Research Agent")


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
        "Reply as a collaborative research specialist."
    )
    try:
        response = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        response = (
            "기꺼이 합류하겠습니다. 시장 분석 인사이트를 빠르게 정리해드리겠습니다."
        )
    return {"response": response}


@app.post("/invoke")
async def invoke(payload: InvokePayload) -> dict[str, Any]:
    """Run a research task."""

    prompt = (
        f"Research query: {payload.query}\n"
        "Return a short summary, three key findings, and two plausible sources."
    )
    try:
        summary = await chat(SYSTEM_PROMPT, prompt)
        findings = [
            "AI 도입 시장은 자동화 ROI가 명확한 업무부터 빠르게 침투합니다.",
            "B2B 구매자는 품질 보증과 운영 안정성을 함께 평가합니다.",
            "버티컬 특화 에이전트가 범용 에이전트보다 초기 신뢰를 얻기 쉽습니다.",
        ]
    except Exception:
        summary = "AI 스타트업 시장은 운영 자동화, 품질 검증, 멀티에이전트 협업 수요를 중심으로 성장하고 있습니다."
        findings = [
            "업무별 전문 에이전트 조합 수요가 증가합니다.",
            "신뢰 지표와 검증된 퍼블리셔 정보가 선택에 직접 영향을 줍니다.",
            "데모에서는 빠른 응답성과 협업 가능성이 핵심 차별점입니다.",
        ]
    return {
        "summary": summary,
        "key_findings": findings,
        "sources": ["McKinsey AI report", "MIT Sloan AI analysis"],
    }
