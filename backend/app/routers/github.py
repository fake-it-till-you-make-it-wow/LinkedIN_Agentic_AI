"""GitHub webhook ingestion (Phase 3-B)."""

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

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Process a GitHub webhook event.

    서명 검증은 Phase 4에서 도입 (현재 PoC 범위 밖).
    """

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid JSON"
        ) from exc

    try:
        if x_github_event == "release":
            return handle_release_event(session, payload)
        if x_github_event == "star":
            return handle_star_event(session, payload)
    except GitHubWebhookError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return {"status": "ignored", "reason": f"event={x_github_event or 'missing'}"}
