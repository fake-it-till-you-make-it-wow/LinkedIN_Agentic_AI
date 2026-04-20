"""결성된 팀 목록 조회 및 삭제 라우터."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_db_session
from backend.app.models import FormedTeam
from backend.app.schemas import TeamRead

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamRead])
def list_teams(session: Session = Depends(get_db_session)) -> list[TeamRead]:
    rows = session.scalars(
        select(FormedTeam).order_by(FormedTeam.created_at.desc())
    ).all()
    return [TeamRead.model_validate(r) for r in rows]


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: str, session: Session = Depends(get_db_session)) -> None:
    team = session.get(FormedTeam, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
