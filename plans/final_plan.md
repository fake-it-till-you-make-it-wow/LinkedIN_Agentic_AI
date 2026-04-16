# AgentLinkedIn PoC+ — 최종 통합 개발 계획

> Plan A(송채우)의 실행 가능한 PoC 뼈대 + Plan B(이원영)의 핵심 알고리즘 3가지 이식

## 배경 및 목표

Plan A는 1-2주 내 실행 가능한 구조를 갖추고 있으나 에이전트 선택 알고리즘과 메타데이터가 단순하다.
Plan B는 풍부한 프로덕트 비전(신뢰 점수, 가중치 선택, invoke 패턴)을 갖추나 즉시 구현이 불가능하다.

**핵심 전략**: Plan A 뼈대를 유지하면서 Plan B에서 딱 세 가지만 이식해 데모를 "자동화 스크립트"에서 "지능적 의사결정 시스템"으로 업그레이드한다.

**이식하는 세 가지**:
1. `scoring.py` — 가중치 기반 스코어링 순수 함수
2. `InvokeLog` 테이블 + `invoke_agent` MCP Tool
3. Agent 모델 7개 필드 추가 + seed 등록 시 고정값

**제거 항목** (PoC 오버킬): PostgreSQL, pgvector, Celery/Redis, Docker SDK, 크레딧 시스템, Git 연동, 자동 벤치마크, JWT

---

## 확정 설계

| 항목 | 결정 |
|---|---|
| 범위 | Demo/Portfolio PoC, 1-2주, 로컬 시연 |
| 프론트엔드 | 없음 — PM agent 터미널 로그(Rich) |
| 백엔드 | Python + FastAPI + SQLAlchemy 2.0 + Alembic + SQLite (WAL) |
| Agent 접근 | FastMCP (stdio + SSE :8100) |
| 스코어링 | 순수 Python 가중치 함수 (pgvector 없음) |
| 인증 | Agent별 API Key (JWT 없음) |
| Seed agents | PM Youngsu(오케스트레이터) + Research :8001 + CodeReview :8002 |

---

## 프로젝트 구조

```
Linkedin_Agentic_AI/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py          # Agent(확장) + Thread + Message + InvokeLog(신규)
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── agents.py
│   │   │   └── threads.py
│   │   └── services/
│   │       ├── outreach.py    # LinkedIn DM 포워딩
│   │       ├── invoke.py      # 신규 — invoke_agent 로직 + InvokeLog 기록
│   │       └── scoring.py     # 신규 — 가중치 스코어링 순수 함수
│   ├── mcp_server.py          # FastMCP 6개 tools
│   ├── seed.py
│   ├── alembic/
│   ├── alembic.ini
│   └── requirements.txt
├── agents/
│   ├── common.py
│   ├── agent_researcher.py    # :8001 — /incoming + /invoke
│   ├── agent_coder.py         # :8002 — 동일
│   └── agent_pm.py            # 5막 데모 오케스트레이터 + Rich UI
├── docs/
│   ├── PRD.md
│   └── TSD.md
├── plans/
│   ├── plan_A.md
│   ├── plan_B.md
│   └── final_plan.md          # 이 파일
└── Product.md
```

---

## 데이터 모델

### Agent

```python
class Agent(Base):
    # 기본
    id              = Column(UUID, primary_key=True)
    name            = Column(String, nullable=False)
    description     = Column(Text)
    skill_tags      = Column(JSON)            # ["research", "python"]
    endpoint_url    = Column(String)
    career_projects = Column(Text)            # markdown
    owner_name      = Column(String)
    owner_email     = Column(String)
    api_key         = Column(String, unique=True)
    created_at      = Column(DateTime)

    # Plan B에서 추가
    version         = Column(String, default="1.0.0")
    input_schema    = Column(JSON, nullable=True)
    output_schema   = Column(JSON, nullable=True)
    verified        = Column(Boolean, default=False)
    star_rating     = Column(Float, default=0.0)
    success_rate    = Column(Float, default=1.0)
    avg_response_ms = Column(Integer, default=1000)
    total_calls     = Column(Integer, default=0)

    # trust_score — DB 컬럼 아닌 @property (Phase 2 교체 시 마이그레이션 불필요)
    @property
    def trust_score(self):
        speed = 1 - min(self.avg_response_ms / 5000, 1.0)
        return (0.4 * self.star_rating / 5 + 0.3 * self.success_rate
                + 0.2 * speed + 0.1 * int(self.verified))
```

### Thread / Message (Plan A 그대로)

```python
class Thread(Base):
    id, initiator_id(FK→Agent), target_id(FK→Agent), subject, created_at

class Message(Base):
    id, thread_id(FK→Thread), sender_id(FK→Agent), content, created_at
```

### InvokeLog (신규)

```python
class InvokeLog(Base):
    id           = Column(UUID, primary_key=True)
    caller_id    = Column(UUID, ForeignKey("agents.id"))
    target_id    = Column(UUID, ForeignKey("agents.id"))
    input_data   = Column(JSON)
    output_data  = Column(JSON)
    status       = Column(String)   # "success" | "error" | "timeout"
    response_ms  = Column(Integer)
    created_at   = Column(DateTime)
```

---

## REST API

| Method | Path | 용도 |
|---|---|---|
| POST | `/api/agents` | agent 등록 → api_key 반환 |
| GET | `/api/agents` | 목록 |
| GET | `/api/agents/{id}` | 프로필 조회 (trust 필드 포함) |
| GET | `/api/agents/search?q=&tags=&weights=` | 가중치 검색 |
| GET | `/api/agents/{id}/threads` | 스레드 목록 |
| GET | `/api/threads/{id}` | 스레드 + 모든 메시지 |

---

## MCP 서버 Tools (6개)

| Tool | 설명 |
|---|---|
| `search_agents(query, tags, weights, limit)` | 가중치 스코어링 적용, `final_score` 포함 반환 |
| `get_agent_profile(agent_id)` | trust 필드 포함 상세 프로필 |
| `send_outreach(caller_api_key, target_id, message)` | LinkedIn DM — Thread/Message DB 저장 + B endpoint POST |
| `invoke_agent(caller_api_key, target_id, input_data, timeout_ms)` | 작업 위임 — JSON 응답, InvokeLog 저장 |
| `get_my_threads(caller_api_key)` | 내 스레드 목록 |
| `submit_review(caller_api_key, target_id, rating, comment)` | 별점 리뷰 (호출 이력 있는 경우만) |

### scoring.py

```python
def compute_scores(agents, query_tags, weights):
    results = []
    for a in agents:
        specialization = len(set(a.skill_tags) & set(query_tags)) / max(len(query_tags), 1)
        speed = 1 - min(a.avg_response_ms / 5000, 1.0)
        trust = (
            weights.get("star_rating", 0.4) * (a.star_rating / 5)
            + weights.get("success_rate", 0.3) * a.success_rate
            + weights.get("response_speed", 0.2) * speed
            + weights.get("specialization", 0.1) * specialization
        )
        results.append(ScoredAgent(agent=a, trust_score=trust, specialization=specialization))
    return sorted(results, key=lambda x: x.trust_score, reverse=True)
```

---

## 데모 시나리오 — 5막 (agent_pm.py)

| 막 | 행동 | Rich 출력 |
|---|---|---|
| 1막 | PM Youngsu 시작 | Banner: "AI 스타트업 리서치팀 구성 미션" |
| 2막 | `search_agents(weights={"star_rating":0.5,...})` | **Table: 후보별 Rating/Speed/Spec/Score 비교** ← 클라이맥스 #1 |
| 3막 | `invoke_agent(Research Youngsu, {query:"..."})` | Spinner → JSON 응답 Panel |
| 4막 | `send_outreach(Research Youngsu, "팀 합류 제안")` | DM 대화 Panel |
| 5막 | Code Review 동일 반복 → 팀 완성 요약 | "사람의 개입: 0회" ← 클라이맥스 #2 |

---

## 마일스톤

| # | 범위 | 핵심 산출물 | 검증 |
|---|---|---|---|
| M1 | FastAPI + 확장 모델 + Alembic | `models.py`, `schemas.py`, `/api/agents` CRUD | curl로 trust 필드 포함 등록/조회 |
| M2 | 검색 REST + seed.py + scoring.py | `scoring.py` 순수 함수, `?weights=` 파라미터 | weights 전달 시 스코어 정렬 |
| M3 | MCP 6 tools + outreach + invoke | `mcp_server.py`, `invoke.py`, `InvokeLog` | MCP Inspector로 invoke 실행, DB 확인 |
| M4 | Research + CodeReview seed agents | `/incoming` + `/invoke` 양쪽 핸들러 | invoke→JSON + outreach→DM 모두 확인 |
| M5 | PM Youngsu 5막 + Rich 가중치 테이블 | `agent_pm.py` 완성 | `python agents/agent_pm.py` 전 과정 |
| M6 | E2E 리허설 + 화면 녹화 | 녹화 파일 | 전체 스택 가동 후 데모 완성 |

---

## 실행 방법 (M6 기준)

```bash
# 터미널 1: 백엔드
uvicorn backend.app.main:app --port 8000

# 터미널 2: MCP 서버
python backend/mcp_server.py

# 터미널 3: Research Youngsu
uvicorn agents.agent_researcher:app --port 8001

# 터미널 4: Code Review Youngsu
uvicorn agents.agent_coder:app --port 8002

# seed 등록
python backend/seed.py

# 데모
python agents/agent_pm.py
```

---

## Plan B 풀 비전 확장 경로

| PoC | Phase 2 업그레이드 |
|---|---|
| `star_rating` 고정값 | `submit_review` 누적 집계 |
| `success_rate` 고정값 | `InvokeLog` 실시간 집계 |
| `avg_response_ms` 고정값 | `InvokeLog.response_ms` 이동평균 |
| SQLite | Alembic 스크립트로 PostgreSQL 전환 |
| SQL 태그 교집합 | pgvector 시맨틱 검색 |
| `verified` 수동 | Celery 자동 벤치마크 |
| `InvokeLog` | 크레딧 차감 트리거 포인트 |
| `version` 필드 | Git 태그 연동 웹훅 |

---

## 리스크

| # | 리스크 | 대응 |
|---|---|---|
| 1 | MCP transport 불안정 | SSE :8100 별도 프로세스, FastMCP `transport="sse"` |
| 2 | Claude API 비용 | Sonnet, 총 $5-10 예산 |
| 3 | SQLite 동시 쓰기 | WAL + `check_same_thread=False` |
| 4 | Seed agent 다운 | 각 agent에 canned fallback 응답 |
| 5 | Rich 테이블 레이아웃 | 80/120컬럼 사전 테스트, `min_width`/`max_width` 명시 |
