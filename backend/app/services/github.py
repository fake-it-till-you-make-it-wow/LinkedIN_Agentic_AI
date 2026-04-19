"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] GitHub 웹훅 이벤트 처리기 (Phase 3-B)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【무엇을 하는 파일인가?】
  GitHub에서 "릴리스 발행" 또는 "★ 추가/삭제" 이벤트가 발생하면
  GitHub가 이 서버로 HTTP POST 요청(=웹훅)을 보냅니다.
  이 파일은 그 요청의 JSON 페이로드를 받아 데이터베이스에 저장하는 로직을 담당합니다.

【데이터 흐름】
  GitHub 이벤트 발생
    → routers/github.py 가 HTTP 요청 수신
    → 이 파일의 handle_release_event() 또는 handle_star_event() 호출
    → SQLite DB 에 저장 (agent_releases 테이블, agents 테이블)

【주의】
  보안을 위한 서명 검증(X-Hub-Signature-256 HMAC)은 Phase 4에서 추가 예정.
  현재는 PoC(Proof of Concept) 단계이므로 서명 없이 처리.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Agent, AgentRelease, new_uuid

# ──────────────────────────────────────────────
# 커스텀 예외 클래스
# ──────────────────────────────────────────────


class GitHubWebhookError(Exception):
    """GitHub 웹훅 페이로드를 처리할 수 없을 때 발생하는 예외.

    예) 필수 필드(github_repo, tag)가 없거나, DB에 매칭되는 에이전트가 없을 때.
    이 예외가 발생하면 routers/github.py 가 HTTP 400 에러로 응답함.
    """


# ──────────────────────────────────────────────
# 내부 유틸 함수 (파일 외부에서 직접 호출하지 않음)
# ──────────────────────────────────────────────


def _agent_by_repo(session: Session, full_name: str) -> Agent | None:
    """GitHub 저장소 이름(예: "octocat/hello-world")으로 에이전트를 조회한다.

    Args:
        session: SQLAlchemy DB 세션
        full_name: GitHub 저장소의 전체 이름 ("owner/repo" 형식)

    Returns:
        일치하는 Agent 객체, 없으면 None
    """
    return session.scalar(select(Agent).where(Agent.github_repo == full_name))


def _parse_iso(raw: str | None) -> datetime:
    """GitHub API가 반환하는 ISO 8601 날짜 문자열을 Python datetime으로 변환한다.

    GitHub는 날짜를 "2024-01-15T09:30:00Z" 형식으로 반환하는데,
    Python의 fromisoformat()은 'Z'를 인식 못하므로 '+00:00'으로 교체 후 파싱.

    Args:
        raw: ISO 형식 날짜 문자열, None이면 현재 시각 반환

    Returns:
        UTC 기준의 datetime 객체
    """
    if not raw:
        return datetime.now(UTC)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


# ──────────────────────────────────────────────
# 핵심 이벤트 처리 함수
# ──────────────────────────────────────────────


def handle_release_event(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """GitHub "release" 이벤트를 받아 agent_releases 테이블에 저장한다.

    【언제 호출되나?】
      GitHub 저장소에 새 릴리스(버전)가 발행(published/released/created)될 때.
      예: v1.2.0 태그를 달고 "Publish release" 버튼을 누를 때.

    【처리 순서】
      1. action이 "published" / "released" / "created" 가 아니면 무시
      2. 페이로드에서 저장소명(full_name)과 태그(tag_name) 추출
      3. DB에서 해당 github_repo를 가진 Agent 검색
      4. 동일한 (agent_id, tag) 조합이 이미 있으면 UPDATE, 없으면 INSERT
      5. 커밋 후 결과 반환

    Args:
        session: SQLAlchemy DB 세션 (routers/github.py에서 주입)
        payload: GitHub가 보낸 JSON 페이로드 전체

    Returns:
        {"status": "ok", "agent_id": ..., "tag": ...}  # 성공
        {"status": "ignored", "reason": ...}            # 무시된 경우
    """

    # 처리할 이벤트 액션인지 확인 (GitHub는 다양한 액션을 같은 이벤트 타입으로 보냄)
    action = payload.get("action")
    if action not in {"published", "released", "created"}:
        return {"status": "ignored", "reason": f"action={action}"}

    # 페이로드에서 저장소 정보와 릴리스 정보 추출
    repo = cast("dict[str, Any]", payload.get("repository") or {})
    release = cast("dict[str, Any]", payload.get("release") or {})
    full_name = cast("str | None", repo.get("full_name"))  # 예: "myorg/my-agent"
    tag = cast("str | None", release.get("tag_name"))  # 예: "v1.2.0"

    # 필수 필드 검증
    if not full_name or not tag:
        raise GitHubWebhookError("repository.full_name과 release.tag_name이 필요합니다")

    # 해당 github_repo를 등록한 에이전트가 DB에 있는지 확인
    agent = _agent_by_repo(session, full_name)
    if agent is None:
        return {"status": "ignored", "reason": "no matching agent"}

    # 동일한 (agent_id, tag) 릴리스 레코드가 이미 있는지 확인 (중복 방지)
    existing = session.scalar(
        select(AgentRelease).where(
            AgentRelease.agent_id == agent.id, AgentRelease.tag == tag
        )
    )

    # 릴리스 날짜 파싱 (published_at 우선, 없으면 created_at 사용)
    published_at = _parse_iso(
        cast("str | None", release.get("published_at") or release.get("created_at"))
    )

    if existing is None:
        # 신규 릴리스 → INSERT
        session.add(
            AgentRelease(
                id=new_uuid(),
                agent_id=agent.id,
                tag=tag,
                name=cast("str | None", release.get("name")),  # 릴리스 제목
                body=cast("str | None", release.get("body")),  # 릴리스 노트 본문
                published_at=published_at,
            )
        )
    else:
        # 기존 릴리스 재발행 → UPDATE (제목, 본문, 날짜 갱신)
        existing.name = cast("str | None", release.get("name", existing.name))
        existing.body = cast("str | None", release.get("body", existing.body))
        existing.published_at = published_at

    session.commit()
    return {"status": "ok", "agent_id": agent.id, "tag": tag}


def handle_star_event(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """GitHub "star" 이벤트를 받아 에이전트의 github_star_count를 갱신한다.

    【언제 호출되나?】
      GitHub 사용자가 저장소에 ★을 추가하거나 취소할 때.

    【처리 순서】
      1. 페이로드에서 저장소명(full_name) 추출
      2. DB에서 해당 github_repo를 가진 Agent 검색
      3. stargazers_count (GitHub가 알려주는 공식 숫자)가 있으면 그 값으로 덮어씀
         없으면 action이 "created"이면 +1, "deleted"이면 -1
      4. 커밋 후 결과 반환

    【community_score와의 연관】
      github_star_count가 바뀌면 Agent.community_score 프로퍼티 값도 자동으로 바뀜.
      community_score = log(star_count + 1) / log(101)  → [0, 1] 범위로 정규화됨.

    Args:
        session: SQLAlchemy DB 세션
        payload: GitHub가 보낸 JSON 페이로드 전체

    Returns:
        {"status": "ok", "agent_id": ..., "star_count": ...}  # 성공
        {"status": "ignored", "reason": ...}                   # 무시된 경우
    """

    action = payload.get("action")
    repo = cast("dict[str, Any]", payload.get("repository") or {})
    full_name = cast("str | None", repo.get("full_name"))

    if not full_name:
        raise GitHubWebhookError("repository.full_name이 필요합니다")

    # 해당 저장소를 등록한 에이전트 조회
    agent = _agent_by_repo(session, full_name)
    if agent is None:
        return {"status": "ignored", "reason": "no matching agent"}

    # stargazers_count: GitHub가 내려주는 현재 총 ★ 수 (가장 정확한 값)
    authoritative = repo.get("stargazers_count")
    if isinstance(authoritative, int):
        # GitHub 공식 숫자로 덮어씀 (0 미만 방지)
        agent.github_star_count = max(0, authoritative)
    elif action == "created":
        # ★ 추가됨 → +1
        agent.github_star_count += 1
    elif action == "deleted":
        # ★ 취소됨 → -1 (0 미만 방지)
        agent.github_star_count = max(0, agent.github_star_count - 1)
    else:
        return {"status": "ignored", "reason": f"action={action}"}

    session.commit()
    return {
        "status": "ok",
        "agent_id": agent.id,
        "star_count": agent.github_star_count,
    }
