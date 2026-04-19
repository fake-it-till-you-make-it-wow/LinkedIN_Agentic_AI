"""Inline researcher worker.

`agents/agent_researcher.py`의 FastAPI 핸들러에서 LLM 호출 로직만
순수 함수로 추출했다. HTTP 프로세스를 띄우지 않고 백엔드 안에서
같은 동작을 재현하기 위함이다.
"""

from __future__ import annotations

from typing import Any

from agents.common import chat

SYSTEM_PROMPT = (
    "You are Dr. Sarah's Research Agent. Provide concise market research with "
    "clear findings and practical recommendations."
)

FALLBACK_SUMMARY = (
    "AI 스타트업 시장은 운영 자동화, 품질 검증, 멀티에이전트 협업 수요를 "
    "중심으로 성장하고 있습니다."
)
FALLBACK_FINDINGS: list[str] = [
    "업무별 전문 에이전트 조합 수요가 증가합니다.",
    "신뢰 지표와 검증된 퍼블리셔 정보가 선택에 직접 영향을 줍니다.",
    "데모에서는 빠른 응답성과 협업 가능성이 핵심 차별점입니다.",
]
FALLBACK_SOURCES: list[str] = [
    "McKinsey AI report",
    "MIT Sloan AI analysis",
]
FALLBACK_OUTREACH = (
    "기꺼이 합류하겠습니다. 시장 분석 인사이트를 빠르게 정리해드리겠습니다."
)


def _parse_research_response(text: str) -> tuple[str, list[str]]:
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


async def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query", ""))
    prompt = (
        f"Research query: {query}\n"
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
        "sources": list(FALLBACK_SOURCES),
    }


async def incoming(payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = str(payload.get("thread_id", ""))
    from_agent = payload.get("from_agent") or {}
    sender_name = str(from_agent.get("name", ""))
    message = str(payload.get("message", ""))
    prompt = (
        f"Thread: {thread_id}\n"
        f"From: {sender_name}\n"
        f"Message: {message}\n"
        "Reply as a collaborative research specialist."
    )
    try:
        response = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        response = FALLBACK_OUTREACH
    return {"response": response}
