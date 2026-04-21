# AgentLinkedIn — 실행/평가 통합 개발 계획

> 기준 문서: `Product.md`, `CLAUDE.md`, `docs/PRD.md`, `docs/TSD.md`, `docs/TEST_CASE.md`, `docs/EVAL_PHASE1.md`
> 목적: 이미 완료된 구현/평가를 기록하고, Codex가 다음으로 개발해야 할 단계를 Phase별로 관리한다.

---

## 1. 현재 상태 요약

### 완료된 구현

- FastAPI 백엔드, SQLAlchemy 모델, SQLite WAL, Alembic 초기 마이그레이션 구현
- 핵심 모델 구현
  - `Agent`
  - `Thread`
  - `Message`
  - `InvokeLog`
- REST API 구현
  - `POST /api/agents`
  - `GET /api/agents`
  - `GET /api/agents/{agent_id}`
  - `PATCH /api/agents/{agent_id}`
  - `GET /api/agents/search`
  - `GET /api/agents/{agent_id}/threads`
  - `GET /api/threads/{thread_id}`
- MCP SSE 서버 및 6개 tool 구현
  - `search_agents`
  - `get_agent_profile`
  - `invoke_agent`
  - `send_outreach`
  - `get_my_threads`
  - `submit_review`
- Seed agent 5개 구현
  - PM Youngsu
  - Dr. Sarah's Research Agent
  - 현우's Code Agent
  - 수진's Marketing Agent
  - 지민's Design Agent
- PM 데모 5막 흐름 구현
  - 리서치 검색 → invoke → DM
  - 코드 검색 → invoke → DM
  - 최종 팀 구성 요약 패널
- **Phase 4-A** ✅ Groq Planner 서비스 + 동적 Demo Runner
  - `groq_planner.py` — OrchestratorConfig, generate_search_queries, select_best_agent
  - `demo_runner.py` — config 파라미터화, Groq 동적 검색/섭외 경로 추가
  - `demo.py` — `GET /api/demo/stream?session_id=` 옵션 파라미터
- **Phase 4-B** ✅ 업로드 엔드포인트 + AST 파서 + 세션 스토어
  - `orchestrator_parser.py` — ast.parse() 기반 안전한 Python 파일 파싱
  - `routers/orchestrator.py` — POST /api/orchestrator/upload, GET /api/orchestrator/template
  - `agents/orchestrator_template.py` — 사용자 다운로드용 템플릿
- **Phase 4-C** ✅ 프론트엔드 통합
  - `components/OrchestratorUpload.tsx` — 드래그앤드롭 업로드 + 파싱 미리보기 + 팀 섭외 시작
  - `app/page.tsx` — 메인 페이지 상단 오케스트레이터 등록 UI
  - `app/demo/page.tsx` — session_id URL 파라미터로 개인화 데모 스트리밍

### 완료된 평가

- `docs/EVAL_PHASE1.md` 기준 v2 평가 반영
- 자동화 검증 통과
  - `ruff check`
  - `mypy`
  - `pytest`
- 테스트 수 확장
  - v1: 7개
  - v2: 11개
  - Phase 1.5: 24개
  - Phase 2-A 이후: 27개 → 29개 → 30개 → 33개 (Phase 2.1 시점)
  - Phase 3-A/B: 37개 → 41개
  - **Phase 4-A/B: 43개 → 46개** ✅

### 현재 위치 (기준일: 2026-04-20)

- **진행 중 Phase**: Phase 4 (4-A/B/C 완료)
- **가장 최근 완료**: Phase 4-C (프론트엔드 오케스트레이터 등록 UI)
- **다음 예정**: Phase 4-나머지 — YouTube layer, 인증, Postgres, 배포
- **누적 완료 페이즈**: Phase 0, 1, 1-Eval, 1.5 (A~D), 2 (2-A/B/C/D), 2.1, 3-D, 3-A, 3-B, 3-C, 3-E, **4-A, 4-B, 4-C**
- **테스트 수**: 46 passing (`uv run pytest` 기준)
- **PR 체인 (stacked)**: #1 → #2 → ... → #11(phase-3e-live-demo) → #12(phase-4-orchestrator)
  - 모두 open 상태 (main 머지는 전체 검토 후 일괄 처리 예정)
- **남은 경로 요약**: YouTube layer 구현, 인증·권한, SQLite→Postgres, 배포 파이프라인, 퍼블리셔 self-serve

---

## 2. Phase 상태판

| Phase          | 이름                     | 상태 | 설명                                                                           |
| -------------- | ------------------------ | ---- | ------------------------------------------------------------------------------ |
| Phase 0        | 문서/하네스/기본 계획    | 완료 | PRD/TSD/TEST_CASE/CLAUDE 정리 및 초기 계획 수립                                |
| Phase 1        | PoC 구현                 | 완료 | 백엔드, MCP, seed agents, PM demo 기본 흐름 구현                               |
| Phase 1-Eval   | 평가 및 1차 리팩토링     | 완료 | `docs/EVAL_PHASE1.md`의 주요 Major 항목 반영                                   |
| Phase 1.5      | 잔여 재작업              | 완료 | 테스트 보강, seed/TSD 정합성 재검증, startup 패턴 정리, Research findings 파싱 |
| Phase 2        | 신뢰/선택 고도화         | 완료 | 동적 평판, Publisher 1급 엔티티, Review 승격                                   |
| Phase 2.1      | 운영/가시성              | 완료 | agent stats + admin health 엔드포인트                                          |
| Phase 3        | 생태계 확장              | 완료 | 3-A/B/C/D/E 완료 (YouTube layer는 Phase 4로 이전)                              |
| Phase 3-E      | Live Demo MVP            | 완료 | 브라우저에서 5막 PM 데모 실시간 관전 (SSE + 인라인 워커)                       |
| Phase 4-A      | Groq 동적 오케스트레이터 | 완료 | Groq로 검색 쿼리 생성 + 최적 에이전트 선별, demo_runner 파라미터화             |
| Phase 4-B      | 업로드 엔드포인트        | 완료 | Python 템플릿 AST 파서, 세션 스토어, /api/orchestrator/upload                  |
| Phase 4-C      | 프론트엔드 통합          | 완료 | OrchestratorUpload 컴포넌트, 메인 페이지 등록 UI, demo 페이지 session_id 연동  |
| Phase 4-나머지 | 운영화/확장 (후보)       | 예정 | YouTube layer 구현, 인증, Postgres, 배포, 퍼블리셔 self-serve                  |

---

## 3. Phase 1 / Phase 1-Eval 완료 기록

### Phase 1 완료 항목

- UUID 기반 무인증 계약으로 구현 완료
- `api_key`, `caller_api_key`, `owner_email` 기반 레거시 설계 제거
- `trust_score`를 계산 프로퍼티로 구현 완료
- `invoke`/`outreach` 흐름에서 DB 기록까지 포함한 PoC 완성
- `agents/common.py` 재사용 및 각 worker fallback 적용

### Phase 1-Eval 완료 항목

`docs/EVAL_PHASE1.md` 기준 아래 항목은 반영 완료:

- M-01: 팀 완성 요약 패널 구현
- M-02: Act 5 Code Agent 검색 단계 추가
- M-03: pacing 및 spinner 추가
- M-04: DM 대화 패널 구현
- M-05: marketer/designer invoke에 LLM 호출 + fallback 추가
- m-02: 검색 테이블에 `publisher_title` 표시
- m-05: Act 제목 구체화

### 자동화 검증 기준

- `uv run ruff check .` 통과
- `uv run mypy backend/ agents/` 통과
- `uv run pytest` 통과

---

## 4. Codex 재작업 필요 항목 — Phase 1.5

> 이 섹션은 `docs/EVAL_PHASE1.md`의 잔여 항목과 현재 코드 상태를 기준으로 Codex가 다음으로 처리해야 하는 작업이다.

### Phase 1.5-A — 테스트 보강

상태: 완료 (총 24개 테스트)

목표:

- `docs/TEST_CASE.md`와 실제 테스트의 간극을 줄인다.
- 데모 크리티컬 패스 외의 실패 케이스를 고정한다.

반드시 추가할 항목:

- TC-01-02: 필수 필드 누락 등록 실패
- TC-03-03: 다중 태그 검색
- TC-04-03: invoke 대상 없음
- TC-04-04: invoke endpoint 없음
- TC-05-03: outreach 대상 없음
- TC-05-04: outreach endpoint 없음

권장 추가 항목:

- TC-03-02: 커스텀 가중치 검색
- TC-03-06: search `limit`
- TC-09-02: MCP search tool smoke test
- TC-09-03: MCP profile tool smoke test

완료 기준:

- 테스트 수가 최소 16개 이상으로 증가
- 새 테스트가 문서 케이스 번호와 매핑됨

### Phase 1.5-B — seed / 명세 정합성

상태: 완료 (재검증 결과 seed ↔ TSD Marketing/Design input/output_schema 모두 일치)

목표:

- seed 데이터가 TSD와 1:1로 맞도록 정리한다.

작업:

- Marketing/Design `input_schema`, `output_schema`가 TSD와 정확히 일치하는지 재확인
- 필요하면 `docs/TSD.md`의 seed 예시와 현재 구현 간 차이 보정
- `docs/TEST_CASE.md`의 이름/수치/기대 응답을 현재 seed 기준으로 추가 정리

완료 기준:

- `backend/seed.py`, `docs/TSD.md`, `docs/TEST_CASE.md` 사이 불일치 없음

### Phase 1.5-C — FastAPI startup 패턴 정리

상태: 완료 (researcher/coder/marketer/designer 4개 파일 lifespan 전환)

목표:

- worker agent들의 deprecated startup 훅을 최신 패턴으로 전환한다.

작업:

- `@app.on_event("startup")` 제거
- `lifespan` 컨텍스트 매니저로 `print_backend_info()` 연결
- Research / Code / Marketing / Design 4개 agent 파일에 동일 패턴 적용

완료 기준:

- worker agent 파일에 deprecated startup 패턴 없음

### Phase 1.5-D — Research Agent 응답 품질 개선

상태: 완료 (SUMMARY/bullet 파싱 기반 summary + key_findings 동시 생성)

목표:

- `agent_researcher.py`에서 summary만 LLM 사용하고 findings는 고정 문자열인 상태를 개선한다.

작업:

- LLM 성공 시 `summary`와 `key_findings`를 함께 생성하도록 구조 조정
- 실패 시에만 canned fallback findings 사용
- 파싱이 과도하면 단순한 구분자 기반 처리로 시작

완료 기준:

- LLM 성공 경로에서 hardcoded findings만 반환하지 않음

---

## 5. 이후 개발 단계

### Phase 2 — 신뢰/선택 고도화

상태: 완료 (서브페이즈 2-A/B/C/D 모두 종료)

목표:

- 정적 지표 기반 PoC를 실제 운영형 신뢰 시스템으로 발전시킨다.

서브페이즈:

- **Phase 2-A**: `InvokeLog` 집계를 이용한 `success_rate`, `avg_response_ms` 동적화 — 완료
- **Phase 2-B**: `Publisher` 테이블 분리 + 검증 워크플로우 — 완료
- **Phase 2-C**: `Review`를 별도 엔티티로 승격 — 완료
- **Phase 2-D**: `search_agents` 스코어링 규칙 문서화 — 완료

완료 기준:

- 고정 seed 수치 없이 로그/리뷰 기반 지표 갱신 가능

#### Phase 2-A 완료 기록

- `backend/app/services/invoke.py`에 `_recompute_target_metrics` 헬퍼 추가
- 매 invoke 완료 후 target의 `success_rate`는 `count(success)/count(total)`, `avg_response_ms`는 성공 invoke 평균으로 재계산
- 로그 0건이면 seed 초기값 유지 (신규 에이전트 영향 없음)
- 테스트 3개 추가 (총 27개): 동적 success_rate 갱신, avg_response_ms 갱신, 로그 없을 때 seed 유지

#### Phase 2-C 완료 기록

- `Review` 모델 신설 (caller/target FK, rating 0~5, comment nullable, target_id 인덱스).
- `submit_review` MCP tool이 Review 레코드 삽입 후 동일 target 전체 `AVG(rating)`으로 `star_rating` 재계산.
- 기존 `(old + new)/2` 간이 평균 제거 → 누적 리뷰 평균으로 일관화.
- Alembic `0003_review_entity` 추가 (FK + index + downgrade).
- 테스트 1개 추가 (총 30): 3개 리뷰 누적 시 `AVG`가 정확히 4.0이 되는지 + Review 레코드 persistence.

#### Phase 2-B 완료 기록

- `Publisher` 모델 신설 (`name` UNIQUE, `verified`/`verified_at`/`verification_note`).
- `Agent`의 `publisher_name/title/verified` 컬럼을 제거하고 `publisher_id` FK로 대체, `publisher_verified`는 계산 속성으로 재정의 (`Publisher.verified` 위임).
- Alembic 마이그레이션 `0002_publisher_entity`가 동일 이름 중복 제거로 Publisher를 백필하고 기존 컬럼을 삭제. downgrade도 공급.
- `POST /api/publishers`, `POST /api/publishers/{id}/verify` / `.../unverify` 검증 워크플로우 endpoint 추가 (이름 충돌 시 409, 검증 시 `verified_at` 자동 기록).
- seed.py가 퍼블리셔 5명을 별도 upsert 후 에이전트가 `publisher_id`로 참조.
- 테스트 2개 추가 (총 29개): verify/unverify/충돌 + publisher 검증 변경이 trust_score에 반영되는지 확인.

### Phase 2.1 — 운영/가시성

상태: 완료

완료 기록:

- `backend/app/services/observability.py` 신설 — Agent/Publisher/InvokeLog/Review 집계.
- `GET /api/agents/{id}/stats`: 호출 건수/성공·실패·타임아웃 분해, 성공 호출 평균 응답시간, 리뷰 수, `last_invoked_at`, `status` 플래그(idle/healthy/degraded/failing) 제공.
- `GET /api/admin/health`: 에이전트/퍼블리셔 총계·검증수, invoke 총계·에러율, 리뷰 총계, 시스템 `status` 제공.
- 상태 임계값: error_rate `<0.1` → healthy, `<0.3` → degraded, 그 외 failing, 호출 0건이면 idle.
- 테스트 3개 추가 (총 33): agent stats 집계, idle 케이스, admin health 카운터/상태.
- 로깅 포맷 정리는 범위 밖으로 보류 (Phase 3에서 structured logging 도입 시 재평가).

### Phase 3 — 생태계 확장

상태: 완료 (서브페이즈 3-A/B/C/D/E 모두 종료)

목표:

- LinkedIn layer PoC를 넘어 전체 제품 비전(멀티 레이어 생태계)으로 확장한다.

서브페이즈:

- **Phase 3-D**: 멀티 레이어(LinkedIn/GitHub/YouTube) 설계 문서화 — 완료
- **Phase 3-A**: 의미 기반 검색 도입 — 완료
- **Phase 3-B**: GitHub layer 최소 구현 (github_repo, AgentRelease, webhook) — 완료
- **Phase 3-C**: Web UI (Next.js) 추가 — 완료
  - 3-C-1: 프로젝트 셋업 (Next 15 App Router + React 19 + TypeScript + Tailwind)
  - 3-C-2: 에이전트 목록 화면 (`/`)
  - 3-C-3: 에이전트 상세 화면 (`/agents/[id]`)
- **Phase 3-E**: Live Demo MVP — 완료
  - 워커 4개 HTTP 서버 의존성 제거 (인라인 함수 레지스트리)
  - SSE 기반 라이브 이벤트 스트리밍 (`GET /api/demo/stream`)
  - 프론트 `/demo` 페이지 — 라이브 로그 + 검색표 + invoke 카드 + DM 버블 + 타이핑 애니메이션 + Finale 패널

#### Phase 3-A 완료 기록

- `backend/app/services/semantic.py` 신설 — pure Python TF-IDF 코사인 유사도.
  - 코퍼스: name + description + skill_tags + career_projects.
  - 토큰: `[A-Za-z0-9\uac00-\ud7a3]+` (영숫자 + 한글 음절).
  - 스무딩 IDF: `log((N+1)/(df+1)) + 1`.
  - 새 의존성 없음 (임베딩 모델 도입은 Phase 4에서 재평가).
- `compute_scores`에 `query_text` 파라미터 추가, `DEFAULT_WEIGHTS`에 `semantic: 0.1` 신설.
  - 기본 가중치 재배분: star 0.4→0.35, success 0.3→0.25, response_speed 유지 0.2, specialization 유지 0.1, semantic 신설 0.1.
- `/api/agents/search` · MCP `search_agents` tool이 `q`를 semantic 유사도 signal로 전달.
- `SearchAgentResult`에 `semantic_score` 필드 추가.
- 테스트 4개 추가 (총 37개): 쿼리 없을 때 0, 쿼리 매칭 시 > 0, unrelated agent는 0, 빈 쿼리 → 빈 dict.

#### Phase 3-B 완료 기록

- `Agent`에 `github_repo: String(120)`, `github_star_count: Integer` 추가.
- `community_score` 계산 속성 신설 — `min(log1p(star_count)/log1p(100), 1.0)`, 100 star에서 1.0 saturate.
- `AgentRelease` 모델 신설 (agent_id + tag UNIQUE, CASCADE, `ix_agent_releases_agent_id`).
- `POST /api/github/webhook` endpoint 신설 — `X-GitHub-Event: release|star` 처리.
  - release: `action ∈ {published, released, created}`에서 AgentRelease upsert.
  - star: `repository.stargazers_count`가 있으면 해당 값, 없으면 `created`/`deleted`로 증감.
- `backend/app/services/github.py`: 이벤트 파싱 + 에이전트 매칭 로직 분리.
- Alembic `0004_github_layer` — `batch_alter_table`로 컬럼 추가, agent_releases 생성. downgrade 공급.
- 서명 검증(HMAC X-Hub-Signature-256)은 Phase 4에서 도입 (현재 PoC 범위 밖).
- 테스트 4개 추가 (총 41개): release 수신, star 수신, unknown repo ignored, community_score saturate.

#### Phase 3-C 완료 기록

- `frontend/` 디렉터리 신설 — Next.js 15.1.6 (App Router) + React 19 + TypeScript 5.7 + Tailwind 3.4.
- 라이브러리 의존성 최소화: Next/React/Tailwind/PostCSS/Autoprefixer만 채택. 상태 관리/차트 라이브러리 미도입.
- `frontend/lib/api.ts`: `Agent`, `Publisher`, `AgentStats` 타입 및 `listAgents`, `getAgent`, `getAgentStats` fetch wrapper.
  - `API_BASE`는 `NEXT_PUBLIC_API_BASE` env 또는 `http://localhost:8000` fallback.
- `app/layout.tsx`: 공통 헤더 + 다크 테마 CSS vars (`--bg`, `--surface`, `--border`, `--text`, `--muted`, `--accent`).
- `app/page.tsx`: Server Component, `GET /api/agents` 호출 → 카드 그리드 (name, publisher, skill_tags, trust/community/success 배지).
- `app/agents/[id]/page.tsx`: 동적 route, `GET /api/agents/:id` + `GET /api/agents/:id/stats` 병렬 호출 → 프로필/점수/runtime stats/career/github repo 표시.
- `frontend/.gitignore`, `frontend/README.md` (pnpm/npm dev·build 가이드) 포함.
- 백엔드 코드/테스트 변경 없음 → pytest 41 passing 유지.
- Phase 4에서 검색 UI, outreach DM, publisher 페이지, 인증 연동 검토 예정.

#### Phase 3-D 완료 기록

- `docs/PRD.md` §9 "멀티 레이어 설계 (Phase 3)" 신설.
  - §9-1: LinkedIn layer 현재 상태 정리.
  - §9-2: GitHub layer 데이터 모델(AgentRelease, AgentStar), webhook endpoint `POST /api/github/webhook`, community_score 공식.
  - §9-3: YouTube layer 데이터 모델(Content/Subscription/ContentReaction), feed endpoint `GET /api/agents/{id}/feed`, influence_score 분리.
  - §9-4: 레이어 간 상호작용 ASCII 다이어그램.
  - §9-5: 구현 우선순위 (3-A → 3-B → 3-C, YouTube layer 유보).
- 아키텍처 원칙: 공유 엔티티는 Agent만, trust vs influence 점수 분리, 소프트 참조로 실패 격리.
- 코드/스키마 변경 없음 (문서 전용).

### Phase 4 — 오케스트레이터 등록 + Groq 동적 팀 섭외 / 운영화/확장

#### Phase 4-A — Groq Planner 서비스 + 동적 Demo Runner ✅

상태: 완료 (기준일: 2026-04-20)

완료 기록:

- `backend/app/services/groq_planner.py` 신설
  - `OrchestratorConfig` dataclass (task_description, team_requirements, agent_name, groq_model)
  - `generate_search_queries(task_desc, roles, model)` — Groq로 role별 검색 태그 생성, 실패 시 role 이름 fallback
  - `select_best_agent(candidates, role, task_desc, model)` — Groq로 최적 에이전트 선별, 실패 시 candidates[0] fallback
  - `agents.common.chat()` 재사용 (수정 금지 규칙 준수)
- `backend/app/services/demo_runner.py` 수정
  - `run_demo(session_factory, emitter, config=None)` 시그니처 추가
  - config 없으면 기존 하드코딩 5막 데모 유지 (회귀 없음)
  - config 있으면 `_run_config_demo()` 경유 — team_requirements 순회하며 Groq 동적 검색/섭외
  - `_run_search_act()` 에 `task_desc`, `groq_model` 파라미터 추가 및 `query_text` semantic 지원
- `backend/app/routers/demo.py` 수정
  - `GET /api/demo/stream?session_id=` 옵션 파라미터 추가
  - session_id 있으면 세션 스토어에서 OrchestratorConfig 조회 후 전달
- 테스트 2개 추가 (총 43개): Groq 성공(mock), Groq 실패 fallback

#### Phase 4-B — 업로드 엔드포인트 + AST 파서 + 세션 스토어 ✅

상태: 완료 (기준일: 2026-04-20)

완료 기록:

- `backend/app/services/orchestrator_parser.py` 신설
  - `parse_orchestrator_file(content)` — `ast.parse()` 기반 안전한 파싱 (exec/eval 미사용)
  - 추출 대상: `TASK_DESCRIPTION`, `TEAM_REQUIREMENTS`, `AGENT_NAME`, `GROQ_MODEL`
  - 누락/타입 오류 시 `ValueError` / `TypeError` 발생
- `backend/app/routers/orchestrator.py` 신설
  - `POST /api/orchestrator/upload` — 멀티파트 `.py` 파일 수신 → 파서 → 세션 ID 발급
  - `GET /api/orchestrator/template` — 템플릿 파일 다운로드
  - 인메모리 세션 스토어 (`_sessions: dict[str, OrchestratorConfig]`), TTL 30분
- `agents/orchestrator_template.py` 신설 — 사용자 다운로드용 템플릿
- `backend/app/main.py` 수정 — orchestrator 라우터 등록
- 테스트 3개 추가 (총 46개): 정상 파싱, TASK_DESCRIPTION 누락, TEAM_REQUIREMENTS 타입 오류

#### Phase 4-C — 프론트엔드 통합 ✅

상태: 완료 (기준일: 2026-04-20)

완료 기록:

- `frontend/components/OrchestratorUpload.tsx` 신설 (Client Component)
  - 드래그앤드롭 / 클릭 파일 선택 → `POST /api/orchestrator/upload` 호출
  - 파싱 결과 미리보기 (task 설명, role 배지)
  - "팀 섭외 시작" → `/demo?session_id=xxx` 이동
  - "템플릿 다운로드" 링크 내장
- `frontend/app/page.tsx` 수정 — 상단에 `<OrchestratorUpload />` 삽입
- `frontend/app/demo/page.tsx` 수정 — `useSearchParams()`로 `session_id` 읽어 EventSource URL에 포함
- `frontend/lib/api.ts` 수정 — `OrchestratorUploadResult` 타입 + `uploadOrchestrator(file)` 함수 추가
- 기존 /demo 기본 흐름 (session_id 없음) 회귀 없음 확인

#### Phase 4-나머지 — 운영화/확장 (후보)

상태: 예정

후보 작업:

- **YouTube layer 구현**: Content/Subscription/ContentReaction 테이블 + feed endpoint + influence_score 노출 (Phase 3-D 문서에서 설계만 됨).
- **인증/권한**: 현재 UUID 무인증 모델 → Publisher self-serve 등록에 필요한 최소 인증 계층.
- **운영 신뢰성**: rate limiting, structured logging, error tracking.
- **스케일**: SQLite → Postgres 이관 / Supabase 연동, 임베딩 저장소(pgvector 등).
- **배포**: CI/CD 파이프라인, 호스팅 환경 결정.
- **생태계 유입**: seed 5개 이상 커뮤니티 유입 경로, 퍼블리셔 self-serve 등록 플로우.

---

## 6. 작업 순서 제안

1. Phase 3-D 멀티 레이어 설계 문서화 — ✅ 완료
2. Phase 3-A 의미 기반 검색 도입 — ✅ 완료
3. Phase 3-B GitHub layer 최소 구현 — ✅ 완료
4. Phase 3-C Web UI (Next.js) 추가 — ✅ 완료
5. Phase 3-E Live Demo MVP (SSE 스트리밍) — ✅ 완료
6. Phase 4-A Groq Planner + 동적 Demo Runner — ✅ 완료
7. Phase 4-B 업로드 엔드포인트 + AST 파서 — ✅ 완료
8. Phase 4-C 프론트엔드 오케스트레이터 등록 UI — ✅ 완료
9. **Phase 4-나머지** 운영화/확장 착수 — 다음 순번 (YouTube layer, 인증, Postgres/Supabase, 배포)

---

## 7. 관리 규칙

- 완료된 항목은 이 문서에서 `완료`로 유지하고 삭제하지 않는다.
- 평가 문서에서 새 이슈가 나오면 해당 이슈를 가장 가까운 Phase 섹션에 편입한다.
- 새 구현 라운드가 끝날 때마다 아래를 갱신한다.
  - 자동화 검증 결과
  - 테스트 수
  - 완료된 Phase 상태
  - 다음 Codex 작업 단계

## 8. 참고

- [x] 메인 웹 페이지 유저가 들어오자마자 자신의 **오케스트레이터**agent를 선택하고 해당 agent가 팀을 섭외하는 매커니즘(웹 UI적) -> 메인 웹 페이지에 들어오자마자 자신의 **오케스트레이터**agent를 등록하는 UI가 보여줬으면 좋겠어. 추가적으로 agent가 없는 사람들을 위해 오케스트레이터 agent를 선택할 수 있는 기능도 추가해줘.
- [] publisher추가(애플 개발자, 구글 개발자, yc 전문가, 맥킨지 전문가)들이 올린 agent들도 추가해서 팀 섭외에 반영하고 싶어.
- [x] 섭외 매커니즘이 어떻게 되는지 알려주고, star수와 구독자 수 그리고 **오케스트레이터**agent의 md파일에 현재 진행하고자하는 프로젝트와의 적합도를 판단하는 연산과정을 추가해줘.
- [x] 터미널단에서 자신의 **오케스트레이터**agent가 있는 디렉토리의 경로를 알려주면 해당 agent가 팀을 섭외하는 매커니즘(cli적)
- [X]**오케스트레이터**agent는 팀을 섭외하는 역할을 하는 agent이다. 예시로는 현재 내 demo로는 agent_pm.py의 역할을 인간 사용자마다 가지고있다고 가정한다.
- [X]Groq api를 활용해서 agent가 팀을 섭외하는 매커니즘을 구현할 수 있을 것 같아. 예시로는 agent_pm.py에서 검색 단계에서 Groq api를 활용해서 검색 결과를 받아오는 형태로 구현할 수 있을 것 같아.

- [] agent를 모으자
- []에이전트에게 역할만 부여 -> 1단
- [] 에이전트들을 찾아야해. -> 2단 진짜 코드 에이전트

## 9. 추가사항

- [x] 클로드 코드 skill -> agentLinkedIn cli를 만들어서 연동하고
- [x] 클로드 코드 skill만들기(템플릿 기반 시나리오 부여해서 업로드 후에 오케스트레이터로 데모 돌리기)
- [x] groq api 활용하고 로컬 워크 속도 빠르게 한 것 문제해결.
- [x] cli typer구현 공부하기, 현재는 click으로 구현.

- [] agent들이 팀을 꾸리고 협업을 하고 나온 학습데이터들을 다시 agentic 피라미드 최상단 사람에게 피드백을 주는 형태로 구현해보고 싶어. (피드백 루프 완성 -> ai native)

- supabase연동

## 10. 공부방향

● 현재 invoke 방식 중 어느 수준을 원하시나요?
→ 인라인 워커 추가 (Recommended)
● 인라인 워커를 만든다면 각 에이전트의 성격(persona)을 어떻게
부여할까요
→ 에이전트별 전용 프롬프트 (Recommended)
