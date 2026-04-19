"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] GitHub 웹훅 수신 라우터 (Phase 3-B)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【무엇을 하는 파일인가?】
  GitHub에서 특정 이벤트(릴리스, 스타)가 발생하면,
  GitHub는 미리 등록된 URL로 HTTP POST 요청을 보냅니다. 이것을 "웹훅(Webhook)"이라고 합니다.
  이 파일은 그 웹훅 요청을 받는 FastAPI 엔드포인트를 정의합니다.

【등록된 URL】
  POST  /api/github/webhook

【처리 흐름】
  1. GitHub → POST /api/github/webhook (JSON 페이로드 + X-GitHub-Event 헤더)
  2. 이 파일이 이벤트 타입(X-GitHub-Event)을 읽음
  3. "release" 이벤트 → services/github.py의 handle_release_event() 호출
     "star"    이벤트 → services/github.py의 handle_star_event() 호출
     그 외            → {"status": "ignored"} 반환

【관련 파일】
  - backend/app/services/github.py : 실제 비즈니스 로직 (DB 저장)
  - backend/app/main.py            : 이 라우터를 앱에 등록하는 곳

【주의】
  GitHub 웹훅 서명 검증(보안)은 Phase 4에서 추가 예정.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db_session
from backend.app.services.github import (
    GitHubWebhookError,
    handle_release_event,
    handle_star_event,
)

# "/api/github" 경로를 공통 prefix로 사용하는 FastAPI 라우터
# tags=["github"] → Swagger UI에서 "github" 그룹으로 묶임
router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),  # GitHub가 보내는 이벤트 종류 헤더
    session: Session = Depends(get_db_session),  # DB 세션 자동 주입 (FastAPI DI)
) -> dict[str, Any]:
    """GitHub 웹훅 이벤트를 수신하고 종류에 맞는 핸들러로 분기한다.

    【GitHub 설정 방법】
      저장소 Settings → Webhooks → Add webhook
      Payload URL: https://your-server.com/api/github/webhook
      Content type: application/json
      Events: "Releases", "Stars" 체크

    【요청 형식】
      POST /api/github/webhook
      Headers:
        X-GitHub-Event: release  (또는 star)
        Content-Type: application/json
      Body: GitHub 이벤트 JSON 페이로드

    【응답 형식】
      성공(릴리스): {"status": "ok", "agent_id": "...", "tag": "v1.2.0"}
      성공(스타):   {"status": "ok", "agent_id": "...", "star_count": 42}
      무시됨:       {"status": "ignored", "reason": "..."}
      실패:         HTTP 400 + {"detail": "에러 메시지"}

    【서명 검증 미구현 안내】
      보안을 위해 GitHub는 X-Hub-Signature-256 헤더로 HMAC 서명을 보냄.
      현재는 PoC 단계이므로 검증하지 않음. Phase 4에서 구현 예정.
    """

    # GitHub 페이로드를 JSON으로 파싱 (형식이 올바르지 않으면 400 에러)
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid JSON"
        ) from exc

    # 이벤트 타입별 처리 분기
    try:
        if x_github_event == "release":
            # GitHub 저장소에 릴리스가 발행됐을 때
            return handle_release_event(session, payload)
        if x_github_event == "star":
            # GitHub 저장소에 ★이 추가되거나 취소됐을 때
            return handle_star_event(session, payload)
    except GitHubWebhookError as exc:
        # 서비스 레이어에서 발생한 처리 불가 에러 → HTTP 400으로 변환
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    # 알 수 없는 이벤트 타입은 조용히 무시 (GitHub는 다양한 이벤트를 보낼 수 있음)
    return {"status": "ignored", "reason": f"event={x_github_event or 'missing'}"}
