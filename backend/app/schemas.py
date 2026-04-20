"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] Pydantic 스키마 — API 요청/응답 데이터 형식 정의
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【Pydantic 스키마란?】
  API에서 주고받는 JSON 데이터의 "설계도"입니다.
  - 클라이언트가 보낸 요청 데이터를 Python 객체로 자동 변환하고 유효성 검사를 합니다.
  - Python 객체를 JSON 응답으로 자동 직렬화(변환)합니다.
  - models.py(DB 테이블)와 달리 스키마는 API 경계에서만 사용됩니다.

【models.py와의 차이】
  models.py  → 데이터베이스 테이블 구조 (SQLAlchemy ORM)
  schemas.py → API 입출력 데이터 구조 (Pydantic BaseModel)
  두 파일은 비슷해 보이지만, 역할이 다릅니다.
  예: DB에는 비밀번호 해시를 저장하지만 API 응답에는 포함하지 않을 수 있음.

【스키마 목록】
  ┌──────────────────────┬────────────────────────────────────────────────┐
  │ 스키마 클래스        │ 사용 위치                                      │
  ├──────────────────────┼────────────────────────────────────────────────┤
  │ PublisherCreate      │ POST /api/publishers 요청 바디                 │
  │ PublisherRead        │ 퍼블리셔 조회 API 응답                         │
  │ PublisherVerifyRequest│ PUT /api/publishers/{id}/verify 요청 바디     │
  │ AgentBase            │ 에이전트 공통 필드 (AgentCreate/Read의 부모)   │
  │ AgentCreate          │ POST /api/agents 요청 바디                     │
  │ AgentUpdate          │ PATCH /api/agents/{id} 요청 바디               │
  │ AgentRead            │ 에이전트 조회 API 응답 (점수 포함)             │
  │ SearchAgentResult    │ 검색 결과 응답 (AgentRead + 검색 점수)         │
  │ MessageRead          │ 메시지 조회 응답                               │
  │ ThreadRead           │ 스레드 상세 조회 응답                          │
  │ ThreadSummary        │ 스레드 목록 조회 응답 (간략 정보)              │
  │ InvokeResult         │ 에이전트 호출(invoke) 결과                     │
  │ OutreachResult       │ 아웃리치(DM) 전송 결과                         │
  │ ReviewResult         │ 리뷰 제출 결과                                 │
  │ AgentStats           │ 에이전트 운영 통계 (admin API)                 │
  │ AdminHealth          │ 전체 시스템 상태 (admin API)                   │
  │ SearchWeights        │ 검색 시 가중치 설정                            │
  └──────────────────────┴────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ──────────────────────────────────────────────
# Publisher 관련 스키마
# ──────────────────────────────────────────────


class PublisherCreate(BaseModel):
    """퍼블리셔 등록 시 클라이언트가 보내는 요청 바디.

    사용: POST /api/publishers
    """

    name: str = Field(min_length=1, max_length=100)  # 퍼블리셔 이름 (필수, 최소 1자)
    title: str | None = Field(
        default=None, max_length=200
    )  # 직함 (선택, 예: "AI Lead @ OpenAI")


class PublisherRead(BaseModel):
    """퍼블리셔 조회 시 서버가 반환하는 응답 형식.

    model_config = ConfigDict(from_attributes=True):
      SQLAlchemy ORM 객체(Publisher)를 이 Pydantic 모델로 자동 변환 가능.
    """

    model_config = ConfigDict(
        from_attributes=True
    )  # ORM 객체 → Pydantic 자동 변환 허용

    id: str
    name: str
    title: str | None
    verified: bool  # 검증된 퍼블리셔인지 (True면 에이전트 신뢰 점수 보너스)
    verified_at: datetime | None
    verification_note: str | None
    created_at: datetime


class PublisherVerifyRequest(BaseModel):
    """퍼블리셔 검증 승인 시 관리자가 보내는 요청 바디.

    사용: PUT /api/publishers/{id}/verify
    """

    note: str | None = Field(default=None, max_length=1000)  # 검증 메모 (선택)


# ──────────────────────────────────────────────
# Agent 관련 스키마
# ──────────────────────────────────────────────


class AgentBase(BaseModel):
    """에이전트 공통 필드. AgentCreate와 AgentRead가 이 클래스를 상속합니다.

    【GitHub 연동 필드 (Phase 3-B)】
      github_repo, github_star_count — GitHub 웹훅을 통해 자동으로 갱신됨.
    """

    name: str = Field(min_length=1, max_length=100)  # 에이전트 이름
    description: str | None = None  # 에이전트 설명
    skill_tags: list[str] = Field(
        default_factory=list
    )  # 기술 태그 (예: ["research", "python"])
    endpoint_url: str | None = None  # 에이전트 HTTP 엔드포인트 URL
    career_projects: str | None = None  # 주요 프로젝트 이력
    publisher_id: str | None = None  # 등록 퍼블리셔 ID (없으면 독립 에이전트)
    version: str = "1.0.0"  # 버전 (기본: 1.0.0)
    input_schema: dict[str, Any] | None = (
        None  # 호출 시 받는 입력 형식 명세 (JSON Schema)
    )
    output_schema: dict[str, Any] | None = (
        None  # 호출 시 반환하는 출력 형식 명세 (JSON Schema)
    )
    verified: bool = False  # 플랫폼 공식 검증 여부
    star_rating: float = Field(
        default=0.0, ge=0.0, le=5.0
    )  # 별점 (0.0~5.0, ge=이상, le=이하)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)  # 성공률 (0.0~1.0)
    avg_response_ms: int = Field(
        default=1000, ge=0
    )  # 평균 응답 시간 (밀리초, 음수 불가)
    total_calls: int = Field(default=0, ge=0)  # 누적 호출 횟수
    github_repo: str | None = Field(
        default=None, max_length=120
    )  # GitHub 저장소 (예: "owner/repo")
    github_star_count: int = Field(default=0, ge=0)  # GitHub ★ 수 (음수 불가)


class AgentCreate(AgentBase):
    """에이전트 등록 시 클라이언트가 보내는 요청 바디.

    사용: POST /api/agents
    AgentBase의 모든 필드를 그대로 사용. 추가 필드 없음.
    """


class AgentUpdate(BaseModel):
    """에이전트 부분 업데이트 시 클라이언트가 보내는 요청 바디.

    사용: PATCH /api/agents/{id}
    모든 필드가 Optional(None 허용)입니다.
    보내지 않은 필드는 기존 값을 그대로 유지합니다.
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    skill_tags: list[str] | None = None
    endpoint_url: str | None = None
    career_projects: str | None = None
    publisher_id: str | None = None
    version: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    verified: bool | None = None
    star_rating: float | None = Field(default=None, ge=0.0, le=5.0)
    success_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    avg_response_ms: int | None = Field(default=None, ge=0)
    total_calls: int | None = Field(default=None, ge=0)
    github_repo: str | None = Field(default=None, max_length=120)
    github_star_count: int | None = Field(default=None, ge=0)


class AgentRead(AgentBase):
    """에이전트 조회 시 서버가 반환하는 응답 형식.

    AgentBase 필드 + DB 전용 필드(id, created_at) + 계산 점수 2개.

    【trust_score】  별점·성공률·응답속도·검증 여부를 종합한 신뢰 지수 (0~1)
    【community_score】 GitHub ★ 수를 로그 정규화한 커뮤니티 점수 (0~1)
    두 점수는 models.py의 Agent 프로퍼티에서 자동 계산됩니다.
    """

    model_config = ConfigDict(
        from_attributes=True
    )  # ORM 객체 → Pydantic 자동 변환 허용

    id: str  # 에이전트 UUID
    created_at: datetime  # 등록 시각
    trust_score: float  # 신뢰 점수 (자동 계산, DB에 없음)
    community_score: float  # 커뮤니티 점수 (자동 계산, DB에 없음)
    publisher: PublisherRead | None = None  # 등록 퍼블리셔 정보 (없으면 None)


class SearchAgentResult(AgentRead):
    """에이전트 검색 결과 응답. AgentRead에 검색 점수 3개가 추가됩니다.

    사용: MCP search_agents 도구 응답, GET /api/agents?query=...

    【점수 3가지 의미】
      specialization_match : 요청한 태그(예: "research")와 에이전트 태그의 일치 비율
      semantic_score       : TF-IDF 기반 의미론적 유사도 점수 (Phase 3-A)
      final_score          : 가중치를 적용한 최종 랭킹 점수 (높을수록 상위)
    """

    specialization_match: float  # 태그 일치도 (0.0~1.0)
    semantic_score: float = 0.0  # 의미 유사도 (0.0~1.0)
    final_score: float  # 최종 랭킹 점수


# ──────────────────────────────────────────────
# Thread & Message 관련 스키마
# ──────────────────────────────────────────────


class MessageRead(BaseModel):
    """메시지 조회 응답 형식."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    thread_id: str  # 이 메시지가 속한 대화 채널 ID
    sender_id: str  # 메시지를 보낸 에이전트 ID
    content: str  # 메시지 본문
    created_at: datetime


class ThreadRead(BaseModel):
    """대화 스레드 상세 조회 응답 형식. 메시지 목록도 포함합니다."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    initiator_id: str  # 대화를 시작한 에이전트
    target_id: str  # 대화 상대방 에이전트
    subject: str  # 대화 주제
    created_at: datetime
    messages: list[MessageRead]  # 이 스레드의 모든 메시지 (시간순)


class ThreadSummary(BaseModel):
    """대화 스레드 목록 조회 응답 형식. 마지막 메시지만 포함합니다.

    사용: get_my_threads MCP 도구, GET /api/threads/{agent_id}
    ThreadRead보다 가벼운 형식으로, 목록 화면에서 사용합니다.
    """

    thread_id: str
    subject: str
    created_at: datetime
    other_agent: AgentRead  # 대화 상대방 에이전트 정보
    last_message: MessageRead | None  # 가장 최근 메시지 (없으면 None)


# ──────────────────────────────────────────────
# MCP 도구 결과 스키마
# ──────────────────────────────────────────────


class InvokeResult(BaseModel):
    """에이전트 호출(invoke_agent) 결과 형식.

    성공하면 output에 에이전트의 응답 데이터가 담깁니다.
    실패하면 status가 "error" 또는 "timeout"이 됩니다.
    """

    invoke_log_id: str  # 이 호출의 InvokeLog 레코드 ID
    output: dict[str, Any] | None  # 에이전트가 반환한 출력 데이터
    status: str  # "success" | "error" | "timeout"
    response_ms: int  # 응답 소요 시간 (밀리초)


class OutreachResult(BaseModel):
    """아웃리치 메시지 전송(send_outreach) 결과 형식."""

    thread_id: str  # 생성된 대화 스레드 ID
    response: str  # 대상 에이전트의 자동 응답 메시지
    status: str  # "ok" | "error"


class ReviewResult(BaseModel):
    """리뷰 제출(submit_review) 결과 형식.

    성공하면 new_star_rating에 갱신된 별점 평균이 담깁니다.
    실패하면 error에 이유가 담깁니다.
    """

    success: bool
    new_star_rating: float | None = None  # 리뷰 반영 후 갱신된 별점 평균
    error: str | None = None  # 실패 시 에러 메시지


# ──────────────────────────────────────────────
# Admin 관련 스키마
# ──────────────────────────────────────────────


class AgentStats(BaseModel):
    """에이전트별 운영 통계. 관리자 대시보드용.

    InvokeLog와 Review 데이터를 집계해서 만들어집니다.
    """

    agent_id: str
    total_invocations: int  # 누적 호출 횟수
    success_count: int  # 성공 횟수
    error_count: int  # 에러 횟수
    timeout_count: int  # 타임아웃 횟수
    success_rate: float  # 성공률 (0.0~1.0)
    avg_response_ms: int | None  # 평균 응답 시간
    review_count: int  # 리뷰 수
    star_rating: float  # 별점 평균
    last_invoked_at: datetime | None  # 마지막 호출 시각
    status: str  # "healthy" | "degraded" | "idle"


class AdminHealth(BaseModel):
    """전체 시스템 상태 요약. 관리자 대시보드용."""

    agents_total: int  # 전체 에이전트 수
    agents_verified: int  # 검증된 에이전트 수
    publishers_total: int  # 전체 퍼블리셔 수
    publishers_verified: int  # 검증된 퍼블리셔 수
    invocations_total: int  # 전체 호출 횟수
    invocation_error_rate: float  # 호출 에러율 (0.0~1.0)
    reviews_total: int  # 전체 리뷰 수
    status: str  # "healthy" | "degraded"


# ──────────────────────────────────────────────
# 검색 가중치 스키마
# ──────────────────────────────────────────────


class TeamMemberRead(BaseModel):
    """팀 구성원 단건 정보."""

    id: str
    name: str
    role: str


class TeamRead(BaseModel):
    """결성된 팀 조회 응답 형식."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    mission: str
    members: list[TeamMemberRead]
    stats: dict[str, int] | None
    created_at: datetime


# ──────────────────────────────────────────────
# 검색 가중치 스키마
# ──────────────────────────────────────────────


class SearchWeights(BaseModel):
    """에이전트 검색 시 각 지표의 가중치 설정.

    【기본 가중치 (합계 = 1.0)】
      star_rating    0.35 — 별점 비중 (35%)
      success_rate   0.25 — 성공률 비중 (25%)
      response_speed 0.20 — 응답 속도 비중 (20%)
      specialization 0.10 — 태그 일치도 비중 (10%)
      semantic       0.10 — 의미 유사도 비중 (10%)

    PM 에이전트(agent_pm.py)가 상황에 따라 가중치를 조정해서 검색합니다.
    예: 급한 작업이면 response_speed를 높임, 중요한 작업이면 star_rating을 높임.
    """

    star_rating: float = 0.35
    success_rate: float = 0.25
    response_speed: float = 0.2
    specialization: float = 0.1
    semantic: float = 0.1

    @field_validator("*")
    @classmethod
    def validate_weight(cls, value: float) -> float:
        """가중치는 음수가 될 수 없다. 음수 입력 시 ValidationError 발생."""
        if value < 0:
            raise ValueError("weights must be non-negative")
        return value
