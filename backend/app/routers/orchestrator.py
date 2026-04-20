"""오케스트레이터 등록 API.

Phase 4-B: 사용자가 업로드한 Python 템플릿 파일을 파싱해 세션을 발급하고,
/api/demo/stream?session_id=... 으로 연결한다.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.services.groq_planner import OrchestratorConfig
from backend.app.services.orchestrator_parser import parse_orchestrator_file

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

# PoC용 인메모리 세션 스토어 (TTL 30분)
_sessions: dict[str, OrchestratorConfig] = {}
_SESSION_TTL = 1800


def get_orchestrator_session(session_id: str) -> OrchestratorConfig | None:
    """session_id에 해당하는 OrchestratorConfig를 반환한다. 없으면 None."""
    return _sessions.get(session_id)


@router.post("/upload")
async def upload_orchestrator(file: UploadFile = File(...)) -> dict[str, object]:
    """Python 템플릿 파일을 업로드해 오케스트레이터 세션을 생성한다.

    Returns:
        session_id, task_description, team_requirements, agent_name
    """
    if not (file.filename or "").endswith(".py"):
        raise HTTPException(status_code=400, detail=".py 파일만 업로드할 수 있습니다")

    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="UTF-8 인코딩 파일만 지원합니다"
        ) from None

    try:
        config = parse_orchestrator_file(content)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = str(uuid.uuid4())
    _sessions[session_id] = config

    loop = asyncio.get_event_loop()
    loop.call_later(_SESSION_TTL, lambda: _sessions.pop(session_id, None))

    return {
        "session_id": session_id,
        "task_description": config.task_description,
        "team_requirements": config.team_requirements,
        "agent_name": config.agent_name,
    }


@router.get("/template")
async def download_template() -> FileResponse:
    """오케스트레이터 Python 템플릿 파일을 다운로드한다."""
    template_path = Path(__file__).parents[3] / "agents" / "orchestrator_template.py"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="템플릿 파일을 찾을 수 없습니다")
    return FileResponse(
        str(template_path),
        media_type="text/x-python",
        filename="orchestrator_template.py",
    )
