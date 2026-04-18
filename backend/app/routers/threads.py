"""Thread-related REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.database import get_db_session
from backend.app.models import Thread
from backend.app.schemas import ThreadRead

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.get("/{thread_id}", response_model=ThreadRead)
def get_thread(thread_id: str, session: Session = Depends(get_db_session)) -> Thread:
    """Return thread detail with all messages."""

    statement = (
        select(Thread)
        .where(Thread.id == thread_id)
        .options(selectinload(Thread.messages))
    )
    thread = session.scalar(statement)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )
    return thread
