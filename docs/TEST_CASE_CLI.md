# TEST_CASE_CLI.md — `ocean` CLI 테스트 케이스

> PRD_CLI.md 기능 요구사항(F-01 ~ F-09) 기반. 체크박스는 구현 진행에 따라 검증된 순간 체크한다.

---

## 0. 공통 선행 조건

- 백엔드가 `http://127.0.0.1:8000` 에서 기동 중 (`uv run uvicorn backend.app.main:app --port 8000`)
- seed 데이터 주입 완료 (`uv run python backend/seed.py`)
- 테스트 전에 캐시 제거: `rm -rf ~/.cache/ocean-cli`

---

## 1. F-01: 스펙 로딩

### TC-01-01: 최초 실행 시 원격 스펙 fetch

- [ ] **When**: `ocean --help` 를 cache 비운 상태에서 실행
- **Then**:
  - stdout에 전체 그룹 목록 (`agents publishers threads teams orchestrator github demo admin`) 노출
  - `~/.cache/ocean-cli/openapi.json` 파일 생성됨
  - `~/.cache/ocean-cli/openapi.meta.json` 에 `fetched_at`, `base_url` 기록됨
  - exit code 0

### TC-01-02: 캐시 히트 (TTL 유효)

- [ ] **Given**: TC-01-01 직후 (캐시 존재, TTL 24h 이내)
- **When**: 백엔드를 내린 뒤 `ocean --help`
- **Then**:
  - 정상 help 출력 (오프라인이지만 캐시로 동작)
  - 네트워크 호출 없음
  - exit code 0

### TC-01-03: `--refresh-spec` 강제 갱신

- [ ] **Given**: 캐시 존재
- **When**: `ocean --refresh-spec spec show`
- **Then**:
  - `openapi.meta.json` 의 `fetched_at` 이 현재 시각으로 갱신됨
  - exit code 0

### TC-01-04: `--offline` + 캐시 없음

- [ ] **Given**: `rm -rf ~/.cache/ocean-cli`, 백엔드 중단
- **When**: `ocean --offline --help`
- **Then**:
  - 에러 메시지: `스펙 파일이 없습니다. --offline 을 해제하거나 --spec 으로 경로를 지정하세요.`
  - exit code 4

### TC-01-05: `--spec <path>` override

- [ ] **Given**: 로컬 `docs/openapi.json` 존재
- **When**: `ocean --spec docs/openapi.json agents list --format json`
- **Then**:
  - 정상 실행
  - 캐시 갱신되지 않음

### TC-01-06: base_url 변경 시 자동 재빌드

- [ ] **Given**: 캐시가 `127.0.0.1:8000` 기준으로 존재
- **When**: `ocean --base-url http://127.0.0.1:8010 spec show` (8010 포트에 서버 없음)
- **Then**:
  - `NetworkError` → exit 3, `127.0.0.1:8010` 에 연결 실패 메시지

---

## 2. F-02: 동적 커맨드 바인딩

### TC-02-01: 최상위 그룹 노출

- [ ] **When**: `ocean --help`
- **Then**: 출력에 다음 8개 그룹이 모두 등장
  - `agents`, `publishers`, `threads`, `teams`, `orchestrator`, `github`, `demo`, `admin`

### TC-02-02: 그룹 내 커맨드 개수

- [ ] **When**: `ocean agents --help`
- **Then**: 최소 7개 커맨드 노출 (list / create / get / update / search / stats / threads)

### TC-02-03: 모든 21개 operation 호출 가능

- [ ] **When**: 각 operation에 대해 `ocean <group> <command> --help` 실행
- **Then**: 21회 모두 exit code 0, 파라미터 설명이 출력됨
- **검증 스크립트 예시**:
  ```bash
  for cmd in \
    "health" \
    "admin health" \
    "agents list" "agents create" "agents get" "agents update" \
    "agents search" "agents stats" "agents threads" \
    "publishers list" "publishers create" "publishers get" \
    "publishers verify" "publishers unverify" \
    "threads get" "teams list" "teams delete" \
    "orchestrator upload" "orchestrator template" \
    "github webhook" "demo stream"; do
    ocean $cmd --help >/dev/null || echo "FAIL: $cmd"
  done
  ```
- **완전한 매핑은 §12 Per-Endpoint Coverage 참조.**

### TC-02-04: operationId 충돌 해결

- [ ] **Given**: 동일 그룹에 같은 이름의 operation 2개 (가상 픽스처)
- **When**: binder 호출
- **Then**: method 접미사 (`-get`, `-post`) 로 충돌 해소됨

### TC-02-05: OpenAPI summary 가 --help 에 반영

- [ ] **When**: `ocean agents list --help`
- **Then**: 출력에 OpenAPI `summary` 또는 `description` 이 포함됨

---

## 3. F-03: 파라미터 바인딩

### TC-03-01: path param → positional

- [ ] **When**: `ocean agents get` (인자 없음)
- **Then**: Typer가 `Missing argument 'AGENT_ID'` 에러, exit 5

### TC-03-02: path param 정상 전달

- [ ] **Given**: 유효한 agent_id (seed 데이터의 Research Agent)
- **When**: `ocean agents get <AGENT_ID> --format json`
- **Then**:
  - 응답 JSON에 `id`, `name`, `publisher_name` 포함
  - exit 0

### TC-03-03: query param 전달

- [ ] **When**: `ocean agents search --q research --format json`
- **Then**: 응답에 Research 관련 에이전트가 포함됨

### TC-03-04: 배열 query 반복

- [ ] **When**: `ocean agents list --skill research --skill code --format json`
- **Then**: 요청 URL에 `skill=research&skill=code` 형태로 전달 (실제 엔드포인트에 해당 파라미터가 없으면 skip)

### TC-03-05: bool flag

- [ ] **When**: `ocean agents list --verified --format json`
- **Then**: `verified=true` 쿼리 전달 (스펙이 bool 필터 제공하는 경우)

### TC-03-06: `--body` 로 POST

- [ ] **When**:
  ```bash
  ocean agents create --body '{"name":"TC Agent","description":"test"}' --format json
  ```
- **Then**: 201 응답, 반환 JSON에 `id` 포함

### TC-03-07: `--body-file` 로 POST

- [ ] **Given**: `/tmp/agent.json` 에 유효한 payload
- **When**: `ocean agents create --body-file /tmp/agent.json --format json`
- **Then**: 201, TC-03-06 동일

### TC-03-08: `--field key=value`

- [ ] **When**: `ocean agents create --field name="TC Agent" --field description="test" --format json`
- **Then**: 정상 생성

### TC-03-09: enum 제약

- [ ] **Given**: 스펙에 enum 필드 (예: `status=pending|active|done`) 있는 엔드포인트
- **When**: 허용되지 않은 값 전달
- **Then**: Typer가 choice 에러, exit 5

### TC-03-10: `--as` 자동 주입

- [ ] **Given**: body 스키마에 `caller_agent_id` 필드
- **When**: `OCEAN_CALLER_AGENT_ID=<uuid> ocean orchestrator upload --body-file plan.json`
- **Then**: 요청 body에 `caller_agent_id` 자동 포함

---

## 4. F-04: 요청 실행

### TC-04-01: 기본 base_url

- [ ] **When**: `ocean admin health`
- **Then**: `http://127.0.0.1:8000/api/admin/health` 호출, 응답 정상

### TC-04-02: `--base-url` override

- [ ] **Given**: 백엔드를 `--port 8010` 으로 기동
- **When**: `ocean --base-url http://127.0.0.1:8010 admin health`
- **Then**: 정상 응답

### TC-04-03: `OCEAN_API_BASE` 환경변수

- [ ] **When**: `OCEAN_API_BASE=http://127.0.0.1:8010 ocean admin health`
- **Then**: 정상 응답 (환경변수가 적용됨)

### TC-04-04: `--dry-run`

- [ ] **When**: `ocean --dry-run agents create --body '{"name":"X"}'`
- **Then**:
  - 네트워크 요청 **없음**
  - stdout에 equivalent `curl` 명령 출력 (method, url, body 포함)
  - exit 0

### TC-04-05: `--verbose`

- [ ] **When**: `ocean -v admin health`
- **Then**: stderr에 요청 method/url/헤더 출력, stdout은 응답

### TC-04-06: `--timeout`

- [ ] **Given**: `--timeout 0.001`
- **When**: `ocean --timeout 0.001 agents list`
- **Then**: 타임아웃 에러, exit 3

---

## 5. F-05: 출력 포맷

### TC-05-01: 기본 Rich 렌더 (TTY)

- [ ] **When**: `ocean agents list` (터미널에서 직접 실행)
- **Then**: Rich Table로 출력

### TC-05-02: non-TTY 자동 전환

- [ ] **When**: `ocean agents list | cat`
- **Then**: JSON 배열 출력 (pipe 감지하여 rich → json)

### TC-05-03: `--format json`

- [ ] **When**: `ocean agents list --format json`
- **Then**: `json.loads()` 가능한 유효 JSON

### TC-05-04: `--format yaml`

- [ ] **When**: `ocean agents list --format yaml`
- **Then**: `yaml.safe_load()` 가능한 유효 YAML

### TC-05-05: `--format raw`

- [ ] **When**: `ocean agents list --format raw`
- **Then**: 서버 응답 본문을 바이트 그대로 출력 (trailing newline 없음)

### TC-05-06: `-q/--quiet`

- [ ] **When**: `ocean -q agents list`
- **Then**: 한 줄 minified JSON

### TC-05-07: `--no-color` / `NO_COLOR`

- [ ] **When**: `NO_COLOR=1 ocean agents list`
- **Then**: ANSI escape 없음

### TC-05-08: 빈 배열 응답

- [ ] **Given**: 데이터 없는 엔드포인트 (ex. teams empty)
- **When**: `ocean teams list`
- **Then**: Rich 모드에서 `(empty)` 표기, JSON 모드에서 `[]`

---

## 6. F-06: SSE 처리

### TC-06-01: 기본 SSE 렌더

- [ ] **When**: `ocean demo stream --max-events 3`
- **Then**:
  - 3개 이벤트 렌더 후 자동 종료
  - exit 0

### TC-06-02: `--raw` SSE 패스스루

- [ ] **When**: `ocean demo stream --raw --max-events 1`
- **Then**: 원본 `data: ...\n\n` 형태 그대로 출력

### TC-06-03: `Ctrl+C` 종료

- [ ] **When**: `ocean demo stream` 실행 중 SIGINT
- **Then**: exit code 130, 버퍼 남은 이벤트 flush

### TC-06-04: `--timeout N`

- [ ] **When**: `ocean demo stream --timeout 2`
- **Then**: 2초 경과 시 자동 종료, exit 0

---

## 7. F-07: 에러 처리

### TC-07-01: 404 응답

- [ ] **When**: `ocean agents get 00000000-0000-0000-0000-000000000000`
- **Then**: Rich Panel로 `404 / agent not found`, exit 1

### TC-07-02: 422 Validation

- [ ] **When**: `ocean agents create --body '{}'` (name 누락)
- **Then**: 422, stderr에 `body.name: field required` 요약, exit 1

### TC-07-03: 500 서버 에러 (모의)

- [ ] **Given**: pytest-httpx 로 500 mock
- **Then**: exit 2

### TC-07-04: 연결 실패

- [ ] **Given**: 백엔드 중단
- **When**: `ocean agents list`
- **Then**:
  - `백엔드에 연결할 수 없습니다. uv run uvicorn backend.app.main:app --port 8000` 메시지
  - exit 3

### TC-07-05: 깨진 스펙

- [ ] **Given**: `~/.cache/ocean-cli/openapi.json` 에 임의 문자열 주입
- **When**: `ocean --help`
- **Then**: `스펙 파일이 손상됐습니다. --refresh-spec 후 재시도하세요.`, exit 4

---

## 8. F-08: 부가 커맨드

### TC-08-01: `describe`

- [ ] **When**: `ocean describe agents create`
- **Then**:
  - 메서드/경로, 파라미터 표, requestBody 스키마, 응답 코드별 스키마 요약
  - exit 0

### TC-08-02: `raw`

- [ ] **When**: `ocean raw GET /healthz`
- **Then**: `{"status":"ok"}` 응답, exit 0

### TC-08-03: `raw` with body

- [ ] **When**: `ocean raw POST /api/agents --body '{"name":"Raw"}'`
- **Then**: 201, JSON 응답

### TC-08-04: `spec show`

- [ ] **When**: `ocean spec show`
- **Then**:
  - 캐시 경로, `fetched_at`, `base_url`, paths 개수, operationId 개수 출력
  - exit 0

### TC-08-05: 셸 자동완성 설치 드라이런

- [ ] **When**: `ocean --show-completion zsh`
- **Then**: zsh 완성 스크립트가 stdout에 출력됨

---

## 9. F-09: 패키징 & 실행

### TC-09-01: `uv run ocean --help`

- [ ] **When**: 레포 루트에서 `uv run ocean --help`
- **Then**: help 출력 정상

### TC-09-02: `python -m cli --help`

- [ ] **When**: `uv run python -m cli --help`
- **Then**: 동일한 help 출력

### TC-09-03: pyproject.toml 반영 확인

- [ ] **When**: `uv tree | grep typer`
- **Then**: typer, rich, httpx, PyYAML 모두 설치됨

---

## 10. 회귀 시나리오 (Smoke Suite)

CI에서 매 PR마다 실행할 최소 세트.

| # | 커맨드 | 기대 |
|---|---|---|
| S1 | `ocean admin health` | `{"status":"ok"}` 포함 |
| S2 | `ocean agents list -q` | JSON 배열 파싱 가능 |
| S3 | `ocean agents create --body '{"name":"S3"}' -q` | 응답에 `id` 포함 |
| S4 | `ocean agents get <S3.id> -q` | S3에서 받은 id 로 조회 가능 |
| S5 | `ocean --dry-run agents create --body '{"name":"S5"}'` | curl 명령 stdout |
| S6 | `ocean demo stream --max-events 1` | 1이벤트 후 exit 0 |
| S7 | `ocean describe agents list` | 파라미터 표 출력 |
| S8 | `ocean --refresh-spec spec show` | fetched_at 갱신 |

---

## 11. 성능 벤치마크

| 지표 | 방법 | 목표 |
|---|---|---|
| Cold start (캐시 miss) | `time ocean --help` | < 1.5s |
| Warm start (캐시 hit) | 동일 | < 250ms |
| `ocean agents list` 왕복 | `time ocean agents list -q` | < 400ms |

---

## 12. Per-Endpoint Coverage (F-11)

> **목표**: OpenAPI 스펙의 21개 operation이 CLI 커맨드로 모두 도달 가능함을 증명. 아래 21개 테스트는 하나라도 실패하면 릴리스 차단.

### TC-13-01: `GET /healthz` → `ocean health`

- [ ] **When**: `ocean health --format json`
- **Then**: `{"status":"ok"}` 수신, exit 0

### TC-13-02: `GET /api/admin/health` → `ocean admin health`

- [ ] **When**: `ocean admin health --format json`
- **Then**: 응답에 `status` 필드 + 카운터(`agents`, `publishers`, `teams`) 포함

### TC-13-03: `GET /api/agents` → `ocean agents list`

- [ ] **When**: `ocean agents list --format json`
- **Then**: JSON 배열, seed 환경에서 길이 ≥ 5

### TC-13-04: `POST /api/agents` → `ocean agents create`

- [ ] **When**: `ocean agents create --field name="TC-13-04 Agent" --format json`
- **Then**: 201, 응답에 `id`, `name="TC-13-04 Agent"`, `created_at` 존재

### TC-13-05: `GET /api/agents/search` → `ocean agents search`

- [ ] **When**: `ocean agents search --q research --limit 3 --format json`
- **Then**: 길이 ≤ 3, 각 원소에 `name` 필드 존재

### TC-13-06: `GET /api/agents/{agent_id}` → `ocean agents get`

- [ ] **Given**: TC-13-04 에서 받은 id
- **When**: `ocean agents get <ID> --format json`
- **Then**: 해당 id의 에이전트 반환

### TC-13-07: `PATCH /api/agents/{agent_id}` → `ocean agents update`

- [ ] **When**: `ocean agents update <ID> --field description="updated" --format json`
- **Then**: 응답의 `description=="updated"`

### TC-13-08: `GET /api/agents/{agent_id}/stats` → `ocean agents stats`

- [ ] **When**: `ocean agents stats <ID> --format json`
- **Then**: `success_rate`, `avg_response_ms`, `total_calls` 필드 존재

### TC-13-09: `GET /api/agents/{agent_id}/threads` → `ocean agents threads`

- [ ] **When**: `ocean agents threads <ID> --format json`
- **Then**: JSON 배열 반환 (빈 배열도 성공)

### TC-13-10: `GET /api/publishers` → `ocean publishers list`

- [ ] **When**: `ocean publishers list --format json`
- **Then**: JSON 배열, 각 원소에 `verified` bool 필드

### TC-13-11: `POST /api/publishers` → `ocean publishers create`

- [ ] **When**: `ocean publishers create --field name="TC Publisher" --field title="Tester" --format json`
- **Then**: 201, 응답의 `verified == false`

### TC-13-12: `GET /api/publishers/{publisher_id}` → `ocean publishers get`

- [ ] **Given**: TC-13-11 id
- **When**: `ocean publishers get <ID> --format json`
- **Then**: 해당 id의 publisher 반환

### TC-13-13: `POST /api/publishers/{publisher_id}/verify` → `ocean publishers verify`

- [ ] **When**: `ocean publishers verify <ID> --field note="Confirmed via LinkedIn" --format json`
- **Then**: 응답 `verified == true`

### TC-13-14: `POST /api/publishers/{publisher_id}/unverify` → `ocean publishers unverify`

- [ ] **When**: `ocean publishers unverify <ID> --format json`
- **Then**: 응답 `verified == false`

### TC-13-15: `GET /api/threads/{thread_id}` → `ocean threads get`

- [ ] **Given**: 존재하는 thread_id (seed 또는 데모 실행 후)
- **When**: `ocean threads get <ID> --format json`
- **Then**: `messages` 배열 포함

### TC-13-16: `GET /api/teams` → `ocean teams list`

- [ ] **When**: `ocean teams list --format json`
- **Then**: JSON 배열 반환

### TC-13-17: `DELETE /api/teams/{team_id}` → `ocean teams delete`

- [ ] **Given**: 테스트용 team_id
- **When**: `ocean teams delete <ID> --yes`
- **Then**: 성공 메시지 + exit 0, `--yes` 없이 TTY 실행 시 확인 프롬프트 등장

### TC-13-18: `POST /api/orchestrator/upload` → `ocean orchestrator upload`

- [ ] **Given**: `/tmp/sample_plan.py` (템플릿 기반)
- **When**: `ocean orchestrator upload --body-file /tmp/sample_plan.py --format json`
- **Then**: 응답에 `session_id`, `team_requirements` 존재

### TC-13-19: `GET /api/orchestrator/template` → `ocean orchestrator template`

- [ ] **When**: `ocean orchestrator template --format raw > /tmp/template.py`
- **Then**: 파일 크기 > 0, 첫 줄이 Python 주석/코드로 파싱 가능

### TC-13-20: `POST /api/github/webhook` → `ocean github webhook`

- [ ] **Given**: 샘플 release payload `/tmp/release.json`
- **When**: `ocean github webhook --body-file /tmp/release.json -H x-github-event=release --format json`
- **Then**: 2xx 응답

### TC-13-21: `GET /api/demo/stream` → `ocean demo stream`

- [ ] **When**: `ocean demo stream --max-events 3 --format raw`
- **Then**: 최소 3개 `data:` 라인 수신 후 정상 종료, exit 0

### TC-13-22: 커버리지 동등성 검사 (자동)

- [ ] **Given**: 현재 openapi.json의 operationId 집합
- **When**: `uv run pytest cli/tests/test_endpoint_coverage.py`
- **Then**:
  - `OperationBinder` 가 등록한 커맨드 수 = 스펙의 operation 수
  - 매핑되지 않은 operation이 0개

---

## 13. 헬프 텍스트 품질 (F-10)

### TC-14-01: Help 카탈로그 완전성

- [ ] **When**: `uv run pytest cli/tests/test_help_catalog.py::test_catalog_covers_all_operations`
- **Then**: 스펙의 모든 operationId가 `CATALOG` 에 존재

### TC-14-02: 언어는 영어

- [ ] **When**: `uv run pytest cli/tests/test_help_catalog.py::test_english_only`
- **Then**: 모든 `short`/`long`/`examples`/`params` 값에 한글·히라가나·한자가 없음

### TC-14-03: 금지 용어 없음

- [ ] **When**: 린터 실행
- **Then**: `endpoint`, `router`, `payload`, `handler`, `dispatcher`, `CRUD`, `DTO`, `ORM` 단어 경계 매치 0건 (`"Examples:"` 같은 자연어 예외는 허용)

### TC-14-04: 예시 1개 이상 + 접두사

- [ ] **When**: 린터 실행
- **Then**:
  - 모든 엔트리 `len(examples) >= 1`
  - 모든 예시는 `$ ocean` 으로 시작

### TC-14-05: DELETE 경고 필수

- [ ] **When**: 린터 실행
- **Then**: `delete_team_*` 엔트리의 `warnings` 에 "cannot be undone" 문구 포함

### TC-14-06: 약어 풀이

- [ ] **When**: 린터 실행
- **Then**: `SSE` 가 등장하는 엔트리(=demo stream)에 "live stream" 또는 "server-sent events" 풀이 존재

### TC-14-07: 루트 help

- [ ] **When**: `ocean --help`
- **Then**:
  - 첫 줄에 "Talk to the AgentLinkedIn backend from your terminal." 또는 동등한 1줄 소개
  - 예시 3개 이상
  - 8개 그룹 + `health` 노출

### TC-14-08: 커맨드 help 구조

- [ ] **When**: 임의 커맨드(예: `ocean agents create --help`)
- **Then**:
  - 첫 줄: `HelpEntry.short`
  - 본문: `HelpEntry.long`
  - `Examples:` 블록에 `examples` 나열
  - 옵션 표: `HelpEntry.params[name]` 설명 적용
  - 경고(있다면): 눈에 띄는 위치(첫 문단 or 맨 아래 박스)

### TC-14-09: 수동 비개발자 리뷰 (체크리스트)

- [ ] QA 담당자가 소프트웨어 개발 경력이 없는 동료에게 `ocean --help` 와 `ocean demo stream --help` 를 보여준다.
- **합격 기준**: 5분 내 아래 질문에 답할 수 있다.
  - "이 도구는 무엇을 하는 것인가?"
  - "`ocean agents list` 를 치면 무엇이 보이는가?"
  - "어떻게 데모를 실행하는가?"

### TC-14-10: Fallback 경고

- [ ] **Given**: 스펙에 `new_feature_op` 가 추가되었지만 `CATALOG` 에 누락
- **When**: `ocean --refresh-spec --help`
- **Then**: stderr에 `warning: no help_catalog entry for 'new_feature_op'` 출력

---

## 14. 수동 검증 체크리스트 (M3 완료 시)

- [ ] Rich 표 출력이 터미널 폭에 맞게 wrap 된다
- [ ] 한글 publisher_name 이 깨지지 않는다
- [ ] `--no-color` 와 `NO_COLOR=1` 모두 동작한다
- [ ] SIGINT 시 "스트림 종료" 메시지가 stderr로 깔끔하게 나온다
- [ ] `--dry-run` curl 명령을 그대로 복사-붙여넣기 하면 같은 응답이 나온다
