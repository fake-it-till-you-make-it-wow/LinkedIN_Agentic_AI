"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] 데이터베이스 마이그레이션 스크립트 — GitHub 연동 레이어 추가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【마이그레이션이란?】
  소프트웨어가 업데이트될 때 데이터베이스 구조(테이블, 컬럼)도 함께 바꿔야 합니다.
  Alembic은 이 변경 작업을 "버전별 스크립트"로 관리하여
  upgrade(적용)와 downgrade(롤백)를 안전하게 실행할 수 있게 해줍니다.

【이 스크립트가 하는 일】
  Phase 3-B에서 GitHub 연동 기능이 추가되면서 두 가지 DB 변경이 필요합니다.

  ① agents 테이블에 컬럼 2개 추가:
     - github_repo       : 에이전트와 연결된 GitHub 저장소 주소
                           예: "openai/gpt-engineer"
     - github_star_count : GitHub ★ 수 (community_score 계산에 사용)

  ② agent_releases 테이블 신규 생성:
     GitHub에서 릴리스가 발행될 때마다 한 행씩 저장됩니다.
     예: v1.0.0, v1.1.0, v2.0.0 각각 한 행

【실행 방법】
  적용:  uv run alembic -c backend/alembic.ini upgrade head
  롤백:  uv run alembic -c backend/alembic.ini downgrade -1

【버전 체인】
  0003_review_entity  →  이 파일(0004_github_layer)  →  (다음 마이그레이션)
  down_revision이 이전 버전을 가리켜 순서를 보장함.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GitHub layer — github_repo/star_count on agents + agent_releases table.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic이 마이그레이션 버전 체인을 추적하기 위한 식별자
revision = "0004_github_layer"  # 이 스크립트의 고유 버전 ID
down_revision = "0003_review_entity"  # 이 스크립트가 의존하는 이전 버전
branch_labels = None
depends_on = None


def upgrade() -> None:
    """DB 스키마를 업그레이드한다 (GitHub 연동 컬럼 + 테이블 추가).

    이 함수는 `alembic upgrade head` 명령 실행 시 호출됩니다.
    """

    # ── ① agents 테이블에 GitHub 관련 컬럼 2개 추가 ──────────────────────
    # batch_alter_table: SQLite는 컬럼 추가 방식이 달라 batch 모드 필요
    with op.batch_alter_table("agents") as batch:
        batch.add_column(
            # 연결된 GitHub 저장소 이름 (예: "octocat/my-agent")
            # nullable=True → 기존 에이전트는 GitHub 저장소가 없어도 됨
            sa.Column("github_repo", sa.String(length=120), nullable=True)
        )
        batch.add_column(
            # GitHub ★ 수 (정수, 기본값 0)
            # server_default="0" → DB 레벨에서도 기본값을 0으로 설정 (기존 행 처리용)
            sa.Column(
                "github_star_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # ── ② agent_releases 테이블 신규 생성 ────────────────────────────────
    op.create_table(
        "agent_releases",
        # id: 각 릴리스의 고유 식별자 (UUID 문자열)
        sa.Column("id", sa.String(length=36), nullable=False),
        # agent_id: 어떤 에이전트의 릴리스인지 (agents.id 참조)
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        # tag: 릴리스 태그 이름 (예: "v1.0.0", "2024.01.15")
        sa.Column("tag", sa.String(length=100), nullable=False),
        # name: 릴리스 제목 (GitHub 릴리스 페이지에 표시되는 이름, 선택)
        sa.Column("name", sa.String(length=200), nullable=True),
        # body: 릴리스 노트 본문 (변경 사항 설명, 선택)
        sa.Column("body", sa.Text(), nullable=True),
        # published_at: 릴리스가 GitHub에 공개된 시각
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        # created_at: 이 DB 레코드가 생성된 시각 (자동 기록)
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # 외래 키: agent_id → agents.id (에이전트가 삭제되면 릴리스도 함께 삭제)
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # 유니크 제약: 같은 에이전트의 같은 태그는 중복 저장 불가
        # 예: "my-agent + v1.0.0" 조합은 DB에 단 하나만 존재
        sa.UniqueConstraint("agent_id", "tag", name="uq_agent_releases_agent_id_tag"),
    )

    # agent_id 컬럼에 인덱스 생성 → "이 에이전트의 모든 릴리스" 조회 시 빠르게 검색
    op.create_index("ix_agent_releases_agent_id", "agent_releases", ["agent_id"])


def downgrade() -> None:
    """DB 스키마를 이전 버전으로 롤백한다 (GitHub 연동 컬럼 + 테이블 제거).

    이 함수는 `alembic downgrade -1` 명령 실행 시 호출됩니다.
    upgrade()의 역순으로 제거합니다.
    """

    # agent_releases 테이블 제거 (인덱스 먼저 삭제해야 함)
    op.drop_index("ix_agent_releases_agent_id", table_name="agent_releases")
    op.drop_table("agent_releases")

    # agents 테이블에서 GitHub 컬럼 제거
    with op.batch_alter_table("agents") as batch:
        batch.drop_column("github_star_count")
        batch.drop_column("github_repo")
