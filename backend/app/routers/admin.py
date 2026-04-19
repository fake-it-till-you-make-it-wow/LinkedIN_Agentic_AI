"""Admin/operator observability routes (Phase 2.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db_session
from backend.app.schemas import AdminHealth
from backend.app.services.observability import compute_admin_health

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health", response_model=AdminHealth)
def admin_health(session: Session = Depends(get_db_session)) -> AdminHealth:
    """Return system-level counters + status flag."""

    return compute_admin_health(session)
