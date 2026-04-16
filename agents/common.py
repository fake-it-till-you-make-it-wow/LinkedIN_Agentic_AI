"""
agents/common.py — LLM 백엔드 추상화 + HTTP 헬퍼

환경변수:
  LLM_BACKEND      : "anthropic" | "groq" | "gemini"  (기본값: "groq")
  ANTHROPIC_API_KEY: Anthropic API 키
  GROQ_API_KEY     : Groq API 키
  GEMINI_API_KEY   : Google Gemini API 키

사용법:
  from agents.common import chat, post_json

  reply = await chat(system="You are ...", user="Hello")
  result = await post_json("http://localhost:8001/invoke", {"query": "..."})
"""

import os
import httpx
from typing import Any

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

LLM_BACKEND: str = os.getenv("LLM_BACKEND", "groq").lower()

# 백엔드별 기본 모델
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "groq":      "llama-3.3-70b-versatile",
    "gemini":    "gemini-1.5-flash",
}

MODEL: str = os.getenv("LLM_MODEL", _DEFAULT_MODELS.get(LLM_BACKEND, ""))

# ---------------------------------------------------------------------------
# 백엔드별 클라이언트 초기화 (임포트 지연 — 사용하는 백엔드만 설치 필요)
# ---------------------------------------------------------------------------

def _make_client() -> Any:
    if LLM_BACKEND == "anthropic":
        try:
            import anthropic  # pip install anthropic
        except ImportError:
            raise ImportError("anthropic 패키지가 없습니다: pip install anthropic")
        return anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if LLM_BACKEND == "groq":
        try:
            from groq import AsyncGroq  # pip install groq
        except ImportError:
            raise ImportError("groq 패키지가 없습니다: pip install groq")
        return AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

    if LLM_BACKEND == "gemini":
        try:
            import google.generativeai as genai  # pip install google-generativeai
        except ImportError:
            raise ImportError("google-generativeai 패키지가 없습니다: pip install google-generativeai")
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        return genai  # 모듈 자체를 클라이언트로 사용

    raise ValueError(f"지원하지 않는 LLM_BACKEND: '{LLM_BACKEND}'. 'anthropic' | 'groq' | 'gemini' 중 선택.")


_client: Any = None

def get_client() -> Any:
    """싱글턴 클라이언트 반환 (첫 호출 시 초기화)."""
    global _client
    if _client is None:
        _client = _make_client()
    return _client


# ---------------------------------------------------------------------------
# 통합 chat 함수 — 모든 seed agent가 이것만 호출
# ---------------------------------------------------------------------------

async def chat(system: str, user: str, model: str | None = None) -> str:
    """
    system prompt + user 메시지를 받아 LLM 응답 텍스트를 반환한다.

    Args:
        system: 에이전트 페르소나/역할 정의
        user:   실제 입력 메시지
        model:  모델 오버라이드 (None이면 LLM_MODEL 환경변수 또는 백엔드 기본값)

    Returns:
        LLM 응답 텍스트 (str)

    Raises:
        RuntimeError: API 호출 실패 시 (호출부에서 canned fallback으로 처리)
    """
    _model = model or MODEL
    client = get_client()

    try:
        if LLM_BACKEND == "anthropic":
            response = await client.messages.create(
                model=_model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text

        if LLM_BACKEND == "groq":
            response = await client.chat.completions.create(
                model=_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                max_tokens=1024,
            )
            return response.choices[0].message.content

        if LLM_BACKEND == "gemini":
            # Gemini는 system instruction을 모델 생성 시 주입
            import google.generativeai as genai
            gemini_model = genai.GenerativeModel(
                model_name=_model,
                system_instruction=system,
            )
            response = await gemini_model.generate_content_async(user)
            return response.text

    except Exception as exc:
        raise RuntimeError(f"[{LLM_BACKEND}] LLM 호출 실패: {exc}") from exc

    raise ValueError(f"알 수 없는 백엔드: {LLM_BACKEND}")


# ---------------------------------------------------------------------------
# HTTP 헬퍼 — seed agent 간 통신 (outreach 포워딩, invoke 포워딩)
# ---------------------------------------------------------------------------

async def post_json(
    url: str,
    payload: dict,
    timeout: float = 30.0,
) -> dict:
    """
    JSON POST 요청을 보내고 응답 dict를 반환한다.

    Args:
        url:     대상 엔드포인트
        payload: 요청 본문 (dict → JSON 직렬화)
        timeout: 초 단위 타임아웃 (기본 30초)

    Returns:
        응답 JSON dict

    Raises:
        httpx.HTTPStatusError:  4xx/5xx 응답
        httpx.TimeoutException: 타임아웃
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# 백엔드 정보 출력 (시작 시 확인용)
# ---------------------------------------------------------------------------

def print_backend_info() -> None:
    """현재 LLM 백엔드 설정을 출력한다. agent 시작 시 호출 권장."""
    key_env = {
        "anthropic": "ANTHROPIC_API_KEY",
        "groq":      "GROQ_API_KEY",
        "gemini":    "GEMINI_API_KEY",
    }.get(LLM_BACKEND, "UNKNOWN")

    key_set = "설정됨" if os.getenv(key_env) else f"미설정 ({key_env} 환경변수 필요)"
    print(f"[common] LLM_BACKEND={LLM_BACKEND}  model={MODEL}  api_key={key_set}")
