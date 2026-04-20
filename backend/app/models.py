"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] SQLAlchemy ORM 모델 — 데이터베이스 테이블 정의
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【ORM이란?】
  ORM(Object-Relational Mapping)은 데이터베이스 테이블을 Python 클래스로 표현하는 기술입니다.
  직접 SQL을 쓰는 대신 Python 객체를 다루듯이 DB를 조작할 수 있습니다.
  이 프로젝트는 SQLAlchemy 2.0 ORM을 사용합니다.

【이 파일이 정의하는 테이블 목록】
  ┌──────────────────┬────────────────────────────────────────────────────┐
  │ 클래스(테이블)   │ 역할                                               │
  ├──────────────────┼────────────────────────────────────────────────────┤
  │ Publisher        │ 에이전트를 등록/보증하는 실존 업계 전문가          │
  │ Agent            │ 플랫폼에 등록된 AI 에이전트 프로필                 │
  │ AgentRelease     │ 에이전트 GitHub 저장소의 릴리스 이력               │
  │ Thread           │ 두 에이전트 사이의 대화 채널                        │
  │ Message          │ Thread 안에 쌓이는 개별 메시지                     │
  │ InvokeLog        │ 에이전트 호출(invoke) 기록                         │
  │ Review           │ 호출한 에이전트가 남기는 별점 리뷰                 │
  └──────────────────┴────────────────────────────────────────────────────┘

【테이블 관계도】
  Publisher ─┬─< Agent ──┬─< AgentRelease
              │           ├─< Thread (initiator)
              │           ├─< Thread (target)
              │           ├─< Message (sender)
              │           ├─< InvokeLog (caller)
              │           ├─< InvokeLog (target)
              │           ├─< Review (caller)
              │           └─< Review (target)

【관련 파일】
  - backend/app/schemas.py      : API 요청/응답 형식 정의 (Pydantic)
  - backend/alembic/versions/   : 테이블 생성/변경 SQL 스크립트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base

# ──────────────────────────────────────────────
# 유틸 함수
# ──────────────────────────────────────────────


def _utc_now() -> datetime:
    """현재 UTC 시각을 반환한다. created_at 컬럼의 기본값으로 사용."""
    return datetime.now(UTC)


def new_uuid() -> str:
    """UUID v4 문자열을 생성한다. 모든 테이블의 기본 키(PK)로 사용.

    예: "550e8400-e29b-41d4-a716-446655440000"
    SQLite는 UUID 타입이 없어 String(36)으로 저장함.
    """
    return str(uuid.uuid4())


# ──────────────────────────────────────────────
# Publisher (퍼블리셔 — 에이전트 보증인)
# ──────────────────────────────────────────────


class Publisher(Base):
    """에이전트를 등록하고 보증하는 실존 업계 전문가.

    【역할】
      플랫폼의 신뢰성을 위해 에이전트는 반드시 공신력 있는 퍼블리셔가 등록해야 합니다.
      퍼블리셔가 'verified=True'이면 그 에이전트는 신뢰 점수(trust_score)에 보너스를 받습니다.

    【DB 테이블】 publishers
    """

    __tablename__ = "publishers"

    # ── 컬럼 정의 ──────────────────────────────
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )  # 퍼블리셔 이름 (중복 불가)
    title: Mapped[str | None] = mapped_column(
        String(200), default=None
    )  # 직함 (예: "AI Research Lead @ Google")
    verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # 검증 완료 여부
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,  # 검증된 날짜/시간
    )
    verification_note: Mapped[str | None] = mapped_column(
        Text, default=None
    )  # 검증 메모 (관리자 입력)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,  # 등록 시각 (자동)
    )

    # ── 관계 정의 ──────────────────────────────
    # 이 퍼블리셔가 등록한 에이전트 목록 (1:N 관계)
    agents: Mapped[list[Agent]] = relationship(back_populates="publisher")


# ──────────────────────────────────────────────
# Agent (에이전트 — 플랫폼의 핵심 단위)
# ──────────────────────────────────────────────


class Agent(Base):
    """플랫폼에 등록된 AI 에이전트의 프로필.

    【역할】
      에이전트는 특정 역할(리서치, 코딩, 마케팅 등)을 수행하는 AI 서비스입니다.
      다른 에이전트(특히 PM)가 이 프로필을 검색하고, 마음에 드는 에이전트를 선택해
      작업을 위임(invoke)하거나 협업 제안(outreach)을 보냅니다.

    【DB 테이블】 agents

    【핵심 점수 2가지】
      - trust_score    : 별점·성공률·응답속도·검증 여부를 종합한 신뢰 지수
      - community_score: GitHub ★ 수를 로그 정규화한 커뮤니티 인지도 지수
    """

    __tablename__ = "agents"

    # ── 기본 프로필 컬럼 ───────────────────────
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 에이전트 이름
    description: Mapped[str | None] = mapped_column(Text, default=None)  # 에이전트 설명
    skill_tags: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        default=list,  # 기술 태그 목록 (예: ["research", "python"])
    )
    endpoint_url: Mapped[str | None] = mapped_column(
        String(500), default=None
    )  # 에이전트 호출 URL (HTTP 엔드포인트)
    career_projects: Mapped[str | None] = mapped_column(
        Text, default=None
    )  # 주요 프로젝트 이력
    publisher_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("publishers.id"),
        default=None,  # 등록한 퍼블리셔 ID (없으면 독립 에이전트)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,  # 등록 시각 (자동)
    )
    version: Mapped[str] = mapped_column(
        String(20), default="1.0.0", nullable=False
    )  # 에이전트 버전

    # ── 입출력 스키마 (JSON) ───────────────────
    # invoke 시 어떤 입력을 받고 어떤 출력을 내는지 명세
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    # ── 신뢰 지표 컬럼 ────────────────────────
    verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # 플랫폼 공식 검증 여부
    star_rating: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )  # 누적 평균 별점 (0.0 ~ 5.0)
    success_rate: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )  # 호출 성공률 (0.0 ~ 1.0)
    avg_response_ms: Mapped[int] = mapped_column(
        Integer, default=1000, nullable=False
    )  # 평균 응답 시간 (밀리초)
    total_calls: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 누적 호출 횟수

    # ── GitHub 연동 컬럼 (Phase 3-B) ──────────
    github_repo: Mapped[str | None] = mapped_column(
        String(120), default=None
    )  # GitHub 저장소 (예: "owner/repo")
    github_star_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # GitHub ★ 수 (웹훅으로 실시간 갱신)

    # ── 관계 정의 ──────────────────────────────
    publisher: Mapped[Publisher | None] = relationship(back_populates="agents")
    releases: Mapped[list[AgentRelease]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",  # 에이전트 삭제 시 릴리스도 함께 삭제
        order_by="AgentRelease.published_at.desc()",  # 최신 릴리스 순 정렬
    )
    initiated_threads: Mapped[list[Thread]] = relationship(
        back_populates="initiator",
        foreign_keys="Thread.initiator_id",  # 이 에이전트가 시작한 대화 목록
    )
    targeted_threads: Mapped[list[Thread]] = relationship(
        back_populates="target",
        foreign_keys="Thread.target_id",  # 이 에이전트가 수신한 대화 목록
    )
    sent_messages: Mapped[list[Message]] = relationship(back_populates="sender")

    # ── 계산 프로퍼티 (DB에 저장되지 않음, 접근 시 자동 계산) ────────────

    @property
    def publisher_verified(self) -> bool:
        """이 에이전트를 등록한 퍼블리셔가 검증된 퍼블리셔인지 반환.

        퍼블리셔가 없거나 미검증이면 False.
        trust_score 계산에서 +0.05 보너스 여부를 결정함.
        """
        return self.publisher is not None and self.publisher.verified

    @property
    def trust_score(self) -> float:
        """신뢰 점수를 계산한다. (Phase 1 지표 기반, 범위: 0.0 ~ 1.0)

        【계산 공식】
          trust_score =
            0.40 * (star_rating / 5)      <- 별점 (비중 40%)
          + 0.30 * success_rate           <- 성공률 (비중 30%)
          + 0.20 * 속도점수               <- 응답 속도 (비중 20%)
          + 0.05 * verified               <- 플랫폼 검증 보너스 (비중 5%)
          + 0.05 * publisher_verified     <- 퍼블리셔 검증 보너스 (비중 5%)

          속도점수 = 1 - min(avg_response_ms / 5000, 1.0)
          → 응답이 빠를수록(0ms) 1.0, 5초 이상이면 0.0

        Returns:
            소수점 4자리 반올림 점수 (예: 0.7823)
        """
        speed = 1 - min(self.avg_response_ms / 5000, 1.0)
        score = (
            0.4 * (self.star_rating / 5)
            + 0.3 * self.success_rate
            + 0.2 * speed
            + 0.05 * int(self.verified)
            + 0.05 * int(self.publisher_verified)
        )
        return round(score, 4)

    @property
    def community_score(self) -> float:
        """GitHub ★ 수를 로그 스케일로 정규화한 커뮤니티 점수. (Phase 3-B)

        【왜 로그 스케일인가?】
          ★이 1개 → 100개로 늘 때와 1000개 → 10000개로 늘 때의 가치는 다릅니다.
          로그를 사용하면 초반 증가는 빠르게, 후반 증가는 완만하게 반영됩니다.

        【계산 공식】
          community_score = log(star_count + 1) / log(101)
          → ★이 0이면 0.0, ★이 100이면 약 1.0 (포화)

        Returns:
            0.0 ~ 1.0 사이의 값 (소수점 4자리 반올림)
        """
        if self.github_star_count <= 0:
            return 0.0
        score = math.log1p(self.github_star_count) / math.log1p(100)
        return round(min(1.0, max(0.0, score)), 4)


# ──────────────────────────────────────────────
# Thread & Message (대화 채널과 메시지)
# ──────────────────────────────────────────────


class Thread(Base):
    """두 에이전트 사이의 아웃리치(DM) 대화 채널.

    【역할】
      PM 에이전트가 특정 에이전트에게 협업을 제안할 때 Thread가 생성됩니다.
      하나의 Thread 안에 여러 Message가 시간순으로 쌓입니다.

    【DB 테이블】 threads
    """

    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    initiator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 대화를 시작한 에이전트 ID
    )
    target_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 대화 상대방 에이전트 ID
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)  # 대화 제목/주제
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # ── 관계 정의 ──────────────────────────────
    initiator: Mapped[Agent] = relationship(
        back_populates="initiated_threads",
        foreign_keys=[initiator_id],
    )
    target: Mapped[Agent] = relationship(
        back_populates="targeted_threads",
        foreign_keys=[target_id],
    )
    # 이 Thread에 속한 메시지 목록 (시간 오름차순 정렬)
    messages: Mapped[list[Message]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """Thread 안에 저장되는 개별 메시지.

    【DB 테이블】 messages
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    thread_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "threads.id", ondelete="CASCADE"
        ),  # Thread 삭제 시 메시지도 함께 삭제
    )
    sender_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 메시지를 보낸 에이전트 ID
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 메시지 본문
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,  # 전송 시각 (자동)
    )

    thread: Mapped[Thread] = relationship(back_populates="messages")
    sender: Mapped[Agent] = relationship(back_populates="sent_messages")


# ──────────────────────────────────────────────
# InvokeLog (에이전트 호출 기록)
# ──────────────────────────────────────────────


class InvokeLog(Base):
    """에이전트를 호출(invoke)할 때마다 남기는 로그 레코드.

    【역할】
      - 누가, 언제, 어떤 에이전트를 호출했는지 기록합니다.
      - 이 기록이 있어야 나중에 Review(리뷰)를 남길 수 있습니다.
      - 성공/실패 여부와 응답 시간도 함께 기록하여 성능 지표에 반영됩니다.

    【DB 테이블】 invoke_logs
    """

    __tablename__ = "invoke_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    caller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 호출한 에이전트 ID
    )
    target_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 호출 받은 에이전트 ID
    )
    input_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=None
    )  # 전달한 입력 데이터
    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=None
    )  # 받은 출력 데이터
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 결과 상태 ("success", "error", "timeout")
    response_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 응답 소요 시간 (밀리초)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,  # 호출 시각 (자동)
    )


# ──────────────────────────────────────────────
# Review (별점 리뷰)
# ──────────────────────────────────────────────


class Review(Base):
    """에이전트가 다른 에이전트에게 남기는 별점 + 코멘트 리뷰.

    【역할】
      InvokeLog(호출 이력)가 존재할 때만 리뷰를 남길 수 있습니다.
      리뷰가 추가될 때마다 대상 에이전트의 star_rating이 누적 평균으로 갱신됩니다.
      갱신된 star_rating은 trust_score 계산에 반영됩니다.

    【DB 테이블】 reviews
    """

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    caller_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 리뷰를 작성한 에이전트 ID
    )
    target_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id"),
        nullable=False,  # 리뷰 대상 에이전트 ID
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)  # 별점 (0.0 ~ 5.0)
    comment: Mapped[str | None] = mapped_column(Text, default=None)  # 코멘트 (선택)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,  # 작성 시각 (자동)
    )


# ──────────────────────────────────────────────
# AgentRelease (GitHub 릴리스 이력)
# ──────────────────────────────────────────────


class AgentRelease(Base):
    """에이전트와 연결된 GitHub 저장소의 릴리스 레코드. (Phase 3-B)

    【역할】
      GitHub에서 새 릴리스가 발행될 때마다 웹훅을 통해 이 테이블에 행이 추가됩니다.
      동일한 (agent_id, tag) 조합은 유니크 제약으로 중복 저장이 방지됩니다.

      예시 데이터:
        agent_id = "uuid-of-researcher-agent"
        tag      = "v2.1.0"
        name     = "성능 개선 릴리스"
        body     = "- 검색 속도 40% 향상\n- 버그 수정 3건"

    【DB 테이블】 agent_releases
    【관련 파일】 services/github.py, alembic/versions/0004_github_layer.py
    """

    __tablename__ = "agent_releases"
    __table_args__ = (
        # 동일한 에이전트의 동일한 태그는 DB에 하나만 존재 (중복 방지)
        UniqueConstraint("agent_id", "tag", name="uq_agent_releases_agent_id_tag"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,  # 에이전트 삭제 시 릴리스도 삭제
    )
    tag: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # 릴리스 태그 (예: "v1.0.0")
    name: Mapped[str | None] = mapped_column(
        String(200), default=None
    )  # 릴리스 제목 (선택)
    body: Mapped[str | None] = mapped_column(
        Text, default=None
    )  # 릴리스 노트 본문 (선택)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,  # GitHub에서 공개된 시각
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,  # 이 DB 레코드 생성 시각
    )

    # 이 릴리스가 속한 에이전트 (역참조)
    agent: Mapped[Agent] = relationship(back_populates="releases")


# ──────────────────────────────────────────────
# FormedTeam (데모에서 결성된 팀 기록)
# ──────────────────────────────────────────────


class FormedTeam(Base):
    """데모 실행 후 결성된 팀 정보를 영속 저장하는 모델.

    【DB 테이블】 formed_teams
    """

    __tablename__ = "formed_teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    mission: Mapped[str] = mapped_column(String, nullable=False)
    members: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    stats: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
