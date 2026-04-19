"""Publisher REST routes + verification workflow."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import get_db_session
from backend.app.models import Publisher
from backend.app.schemas import PublisherCreate, PublisherRead, PublisherVerifyRequest

router = APIRouter(prefix="/api/publishers", tags=["publishers"])


def _get_publisher_or_404(session: Session, publisher_id: str) -> Publisher:
    publisher = session.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Publisher not found"
        )
    return publisher


@router.post("", response_model=PublisherRead, status_code=status.HTTP_201_CREATED)
def create_publisher(
    payload: PublisherCreate, session: Session = Depends(get_db_session)
) -> Publisher:
    """Register a new publisher. Starts unverified."""

    publisher = Publisher(name=payload.name, title=payload.title)
    session.add(publisher)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Publisher name already exists",
        ) from exc
    session.refresh(publisher)
    return publisher


@router.get("", response_model=list[PublisherRead])
def list_publishers(session: Session = Depends(get_db_session)) -> list[Publisher]:
    return list(session.scalars(select(Publisher).order_by(Publisher.created_at)).all())


@router.get("/{publisher_id}", response_model=PublisherRead)
def get_publisher(
    publisher_id: str, session: Session = Depends(get_db_session)
) -> Publisher:
    return _get_publisher_or_404(session, publisher_id)


@router.post("/{publisher_id}/verify", response_model=PublisherRead)
def verify_publisher(
    publisher_id: str,
    payload: PublisherVerifyRequest | None = None,
    session: Session = Depends(get_db_session),
) -> Publisher:
    """Mark a publisher as verified with an optional evidence note."""

    publisher = _get_publisher_or_404(session, publisher_id)
    publisher.verified = True
    publisher.verified_at = datetime.now(UTC)
    if payload is not None:
        publisher.verification_note = payload.note
    session.commit()
    session.refresh(publisher)
    return publisher


@router.post("/{publisher_id}/unverify", response_model=PublisherRead)
def unverify_publisher(
    publisher_id: str, session: Session = Depends(get_db_session)
) -> Publisher:
    """Revoke a publisher's verification."""

    publisher = _get_publisher_or_404(session, publisher_id)
    publisher.verified = False
    publisher.verified_at = None
    publisher.verification_note = None
    session.commit()
    session.refresh(publisher)
    return publisher
