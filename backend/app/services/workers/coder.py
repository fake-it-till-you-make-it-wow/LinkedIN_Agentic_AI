"""Inline code-review worker.

`agents/agent_coder.py`의 FastAPI 핸들러 로직을 순수 함수로 옮긴
것이다. common.py의 chat() 래퍼를 그대로 사용하므로 LLM 동작은
기존 HTTP 워커와 완전히 동일하다.
"""

from __future__ import annotations

from typing import Any

from agents.common import chat

SYSTEM_PROMPT = (
    "You are Hyunwoo's Code Agent. Produce pragmatic architecture and code review "
    "feedback with clear action items."
)

FALLBACK_REVIEW = (
    "구조는 명확하지만 서비스 계층과 입출력 검증을 더 분리하면 유지보수성이 올라갑니다."
)
FALLBACK_SUGGESTIONS: list[str] = [
    "서비스 계층에서 외부 호출과 DB 쓰기를 분리하세요.",
    "입력 스키마 검증을 API와 MCP 양쪽에서 동일하게 유지하세요.",
    "invoke/outreach 실패 케이스를 테스트로 고정하세요.",
]
FALLBACK_OUTREACH = (
    "합류 가능합니다. 코드 구조와 품질 게이트를 맡아 안정적으로 지원하겠습니다."
)


async def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    language = str(payload.get("language", "python"))
    code = str(payload.get("code", ""))
    prompt = (
        f"Language: {language}\n"
        f"Code:\n{code}\n"
        "Return one review summary and three concrete improvement suggestions."
    )
    try:
        review = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        review = FALLBACK_REVIEW
    return {"review": review, "suggestions": list(FALLBACK_SUGGESTIONS)}


async def incoming(payload: dict[str, Any]) -> dict[str, Any]:
    thread_id = str(payload.get("thread_id", ""))
    from_agent = payload.get("from_agent") or {}
    sender_name = str(from_agent.get("name", ""))
    message = str(payload.get("message", ""))
    prompt = (
        f"Thread: {thread_id}\n"
        f"From: {sender_name}\n"
        f"Message: {message}\n"
        "Reply as a senior engineer who can join the team."
    )
    try:
        response = await chat(SYSTEM_PROMPT, prompt)
    except Exception:
        response = FALLBACK_OUTREACH
    return {"response": response}
