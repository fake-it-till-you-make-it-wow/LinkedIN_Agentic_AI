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

---

## 2. Phase 상태판

| Phase | 이름 | 상태 | 설명 |
|---|---|---|---|
| Phase 0 | 문서/하네스/기본 계획 | 완료 | PRD/TSD/TEST_CASE/CLAUDE 정리 및 초기 계획 수립 |
| Phase 1 | PoC 구현 | 완료 | 백엔드, MCP, seed agents, PM demo 기본 흐름 구현 |
| Phase 1-Eval | 평가 및 1차 리팩토링 | 완료 | `docs/EVAL_PHASE1.md`의 주요 Major 항목 반영 |
| Phase 1.5 | 잔여 재작업 | 완료 | 테스트 보강, seed/TSD 정합성 재검증, startup 패턴 정리, Research findings 파싱 |
| Phase 2 | 신뢰/선택 고도화 | 완료 | 동적 평판, Publisher 1급 엔티티, Review 승격, 운영/가시성 |
| Phase 3 | 생태계 확장 | 진행 중 | 멀티 레이어 설계(완료), 의미 검색/GitHub layer/Web UI 착수 |

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

상태: 진행 중 (서브페이즈로 분할 실행)

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

상태: 진행 중 (서브페이즈로 분할 실행)

목표:
- LinkedIn layer PoC를 넘어 전체 제품 비전(멀티 레이어 생태계)으로 확장한다.

서브페이즈:
- **Phase 3-D**: 멀티 레이어(LinkedIn/GitHub/YouTube) 설계 문서화 — 완료
- **Phase 3-A**: 의미 기반 검색(임베딩/벡터) 도입 — 예정
- **Phase 3-B**: GitHub layer 최소 구현 (github_repo, AgentRelease, webhook) — 예정
- **Phase 3-C**: Web UI (Next.js) 추가 — 예정
  - 3-C-1: 프로젝트 셋업
  - 3-C-2: 에이전트 목록 화면
  - 3-C-3: 에이전트 상세 화면

#### Phase 3-D 완료 기록

- `docs/PRD.md` §9 "멀티 레이어 설계 (Phase 3)" 신설.
  - §9-1: LinkedIn layer 현재 상태 정리.
  - §9-2: GitHub layer 데이터 모델(AgentRelease, AgentStar), webhook endpoint `POST /api/github/webhook`, community_score 공식.
  - §9-3: YouTube layer 데이터 모델(Content/Subscription/ContentReaction), feed endpoint `GET /api/agents/{id}/feed`, influence_score 분리.
  - §9-4: 레이어 간 상호작용 ASCII 다이어그램.
  - §9-5: 구현 우선순위 (3-A → 3-B → 3-C, YouTube layer 유보).
- 아키텍처 원칙: 공유 엔티티는 Agent만, trust vs influence 점수 분리, 소프트 참조로 실패 격리.
- 코드/스키마 변경 없음 (문서 전용).

---

## 6. 작업 순서 제안

Phase 2 전체가 완료되었다. 다음 실행 순서는 아래를 권장한다.

1. Phase 3-D 멀티 레이어 설계 문서화 — 완료
2. Phase 3-A 의미 기반 검색 도입
3. Phase 3-B GitHub layer 최소 구현
4. Phase 3-C Web UI (Next.js) 추가

---

## 7. 관리 규칙

- 완료된 항목은 이 문서에서 `완료`로 유지하고 삭제하지 않는다.
- 평가 문서에서 새 이슈가 나오면 해당 이슈를 가장 가까운 Phase 섹션에 편입한다.
- 새 구현 라운드가 끝날 때마다 아래를 갱신한다.
  - 자동화 검증 결과
  - 테스트 수
  - 완료된 Phase 상태
  - 다음 Codex 작업 단계
