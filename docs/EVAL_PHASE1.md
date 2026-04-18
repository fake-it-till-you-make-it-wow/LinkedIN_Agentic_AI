# EVAL_PHASE1.md — Phase 1 PoC 평가 리포트 (v2 — 리팩토링 후)

> 평가자: Claude (Evaluator)
> 대상: Codex (Generator)가 생성 + 리팩토링한 Phase 1 PoC
> 평가일: 2026-04-17
> 기준: 데모 시나리오 적합도 > PRD/TSD 명세 일치 > 코드 품질

---

## 자동화 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `uv run ruff check .` | PASS | 0 errors |
| `uv run ruff format --check .` | **FAIL** | agent_marketer.py, test_services.py 2파일 미포맷 |
| `uv run pytest -v` | PASS | 11/11 tests (v1: 7개 → v2: 11개) |

---

## v1 → v2 수정 현황

| v1 이슈 | 등급 | v2 상태 | 판정 |
|---|---|---|---|
| M-01. 팀 완성 요약 패널 부재 | Major | `_summary_panel()` 구현 — 팀원 목록 + "사람의 개입: 0회" | **RESOLVED** |
| M-02. Act 5 Code Agent 검색 누락 | Major | `_run_cycle()`로 search→invoke→outreach 반복 구조화 | **RESOLVED** |
| M-03. 드라마틱 pacing 없음 | Major | `_pace()` (asyncio.sleep 1.5s) + `console.status` spinner | **RESOLVED** |
| M-04. DM 대화 형식 미구현 | Major | `_dm_panel()` — sender 구분된 대화 패널 | **RESOLVED** |
| M-05. marketer/designer invoke LLM 미사용 | Major | LLM 호출 + try/except fallback 패턴 적용 | **RESOLVED** |
| M-06. 테스트 커버리지 부족 (7/39) | Major | 11개로 증가 — timeout, outreach error, rating range 추가 | **PARTIAL** |
| m-01. deprecated on_event | Minor | 미수정 (동작에 영향 없음) | OPEN |
| m-02. publisher_title 미포함 | Minor | Table에 "Title" 컬럼 추가 | **RESOLVED** |
| m-03. Marketing/Design seed schema 누락 | Minor | 미확인 (seed.py 미변경) | OPEN |
| m-04. researcher findings hardcoded | Minor | 미수정 | OPEN |
| m-05. Act 제목 generic | Minor | 구체적 제목 적용 ("가중치 기반 리서치 탐색" 등) | **RESOLVED** |

---

## 잔여 이슈

### Major (1건)

#### M-06 (잔여). 테스트 커버리지 — 11/39 (28%)

v1의 18% → 28%로 개선. 추가된 테스트:
- `test_trust_score_boundaries` — TC-02-03, TC-02-04 커버
- `test_invoke_agent_timeout` — TC-04-02 커버
- `test_send_outreach_endpoint_error_persists_system_message` — TC-05-05 커버
- `test_submit_review_rejects_invalid_rating` — TC-06-03 커버

**아직 미커버**:
- TC-01-02: 필수 필드 누락 등록 실패
- TC-03-02~06: 커스텀 가중치/다중 태그/복합 검색/limit
- TC-04-03~04: invoke 대상 없음/endpoint 없음
- TC-05-02~04: outreach thread 재사용/대상 없음/endpoint 없음
- TC-09-01~04: MCP 서버 연결 테스트
- TC-E2E-01~03: E2E 통합 테스트

### Minor (3건)

#### m-01 (잔여). deprecated `@app.on_event("startup")`

4개 agent 파일 모두 해당. FastAPI lifespan 패턴으로 전환 권장.

#### m-03 (잔여). Marketing/Design seed에 input_schema/output_schema 누락

seed.py에 Marketing/Design 에이전트의 스키마가 없음. TSD 10절 명세와 불일치.

#### m-04 (잔여). researcher invoke — findings hardcoded

LLM 성공 시에도 key_findings가 hardcoded 리스트. 완전한 LLM 파싱이 아님.

### Format (1건)

#### f-01 (신규). ruff format 미통과 2파일

`agent_marketer.py`, `test_services.py`가 format check 미통과. `uv run ruff format .` 실행 필요.

---

## 종합 평가

| 영역 | v1 | v2 | 변화 |
|---|---|---|---|
| **데모 시나리오 적합도** | 65 | **90** | +25 (요약 패널, DM, pacing, 검색 반복) |
| **PRD 명세 일치** | 80 | **90** | +10 (5막 구조 완성) |
| **TSD 명세 일치** | 75 | **88** | +13 (spinner, publisher_title, Act 제목) |
| **코드 품질** | 90 | **92** | +2 (구조화 개선 — dataclass, helper 분리) |
| **테스트 커버리지** | 40 | **55** | +15 (11/39) |

**종합: 83/100 (v1: 70) — 데모 실행 가능 수준 도달**

---

## Codex 재작업 지시 (남은 항목)

### 즉시 (format 수정)
1. **f-01**: `uv run ruff format .` 실행

### 다음 단계
2. **M-06**: 테스트 추가 — 최소 TC-01-02, TC-03-03, TC-04-03, TC-05-03 커버
3. **m-03**: seed.py에 Marketing/Design input_schema/output_schema 추가
4. **m-01**: `@app.on_event("startup")` → lifespan 패턴 전환
