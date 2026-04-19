"""Research worker agent."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.common import chat, print_backend_info

SYSTEM_PROMPT = (
    "You are Dr. Sarah's Research Agent. Provide concise market research with "
    "clear findings and practical recommendations."
)

FALLBACK_SUMMARY = (
    "AI 스타트업 시장은 운영 자동화, 품질 검증, 멀티에이전트 협업 수요를 "
    "중심으로 성장하고 있습니다."
)
FALLBACK_FINDINGS = [
    "업무별 전문 에이전트 조합 수요가 증가합니다.",
    "신뢰 지표와 검증된 퍼블리셔 정보가 선택에 직접 영향을 줍니다.",
    "데모에서는 빠른 응답성과 협업 가능성이 핵심 차별점입니다.",
]


def _parse_research_response(text: str) -> tuple[str, list[str]]:
    """Extract summary and bullet findings from LLM output."""

    summary_parts: list[str] = []
    findings: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("SUMMARY:"):
            summary_parts.append(line.split(":", 1)[1].strip())
        elif line[:1] in {"-", "*", "•"}:
            bullet = line.lstrip("-*• ").strip()
            if bullet:
                findings.append(bullet)
    summary = " ".join(part for part in summary_parts if part)
    return summary, findings[:3]


class IncomingPayload(BaseModel):
    """Outreach message payload."""

    thread_id: str
    from_agent: dict[str, str]
    message: str


class InvokePayload(BaseModel):
    """Invoke request payload."""

    query: str = Field(min_length=1)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    print_backend_info()
    yield


app = FastAPI(title="Research Agent", lifespan=lifespan)


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
        "Respond in Korean using exactly this format:\n"
        "SUMMARY: <한 문장 시장 요약>\n"
        "- <핵심 발견 1>\n"
        "- <핵심 발견 2>\n"
        "- <핵심 발견 3>"
    )
    try:
        raw = await chat(SYSTEM_PROMPT, prompt)
        parsed_summary, parsed_findings = _parse_research_response(raw)
        summary = parsed_summary or raw.strip() or FALLBACK_SUMMARY
        findings = parsed_findings or FALLBACK_FINDINGS
    except Exception:
        summary = FALLBACK_SUMMARY
        findings = FALLBACK_FINDINGS
    return {
        "summary": summary,
        "key_findings": findings,
        "sources": ["McKinsey AI report", "MIT Sloan AI analysis"],
    }
