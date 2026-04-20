# PRD_CLI — AgentLinkedIn CLI (`ocean`)

> 터미널에서 AgentLinkedIn 백엔드의 모든 REST 엔드포인트를 호출하는 Python CLI

---

## 1. 제품 비전

### 핵심 문제

AgentLinkedIn PoC는 FastAPI 백엔드(`:8000`)와 Next.js 프론트엔드, MCP 서버(`:8100`)로 구성되어 있다. 하지만 **디버깅·데모·자동화** 상황에서는 UI를 띄우지 않고 터미널에서 바로 API를 호출하고 싶다.

현재 대안은 `curl`/`httpie`이지만:

- 엔드포인트 이름·스키마를 매번 기억하거나 Swagger를 열어야 한다
- 결과가 raw JSON이라 가독성이 떨어진다
- SSE 스트리밍 엔드포인트(`/api/demo/stream`)는 파싱이 번거롭다
- 테스트 시나리오를 스크립트화하려면 보일러플레이트가 많다

### 해결하는 것

> **`ocean` CLI: 백엔드가 노출하는 `openapi.json`을 런타임에 읽어, 모든 엔드포인트를 `ocean <group> <command>` 형태의 서브커맨드로 제공하는 단일 도구.**

핵심 차별점:

- **Zero drift**: 스펙에서 직접 파생되므로 백엔드 변경 시 CLI 수정 불필요
- **Rich UX**: 기본 출력은 표/패널, `--format json` 으로 파이프 친화 전환
- **SSE 네이티브**: `/api/demo/stream` 같은 이벤트 스트림을 별도 파서 없이 출력
- **인증 없음**: CLAUDE.md 규칙대로 UUID(`caller_agent_id`)만 선택적 주입

### 한 줄 비전

> **하나의 바이너리로 AgentLinkedIn 백엔드 전체를 조작한다.**

---

## 2. 사용자 및 시나리오

### 2-1. 대상 사용자

| 페르소나 | 주요 용도 |
|---|---|
| **백엔드 개발자** | 새 엔드포인트 구현 후 즉석 smoke test |
| **Planner(Claude) / Evaluator** | TEST_CASE.md 검증 자동화 스크립트 작성 |
| **Generator(Codex)** | 마일스톤 완료 후 회귀 검증 일괄 실행 |
| **데모 발표자** | Swagger UI 없이 터미널에서 주요 플로우 시연 |

### 2-2. 대표 시나리오

**S1 — 에이전트 목록 확인**
```bash
$ ocean agents list
┌──────────────┬───────────────────────────┬────────┬─────────┐
│ name         │ publisher_name            │ trust  │ verified│
├──────────────┼───────────────────────────┼────────┼─────────┤
│ Research     │ Dr. Sarah Chen            │ 0.87   │ ✓       │
│ Code         │ 김현우                    │ 0.82   │ ✓       │
└──────────────┴───────────────────────────┴────────┴─────────┘
```

**S2 — 에이전트 검색 후 상세 조회**
```bash
$ ocean agents search --q "research" --format json | jq '.[0].id'
"2f1c...-a8e3"
$ ocean agents get 2f1c...-a8e3
```

**S3 — 퍼블리셔 등록 & 검증**
```bash
$ ocean publishers create --body-file publisher.json
$ ocean publishers verify <id>
```

**S4 — 오케스트레이션 라이브 데모**
```bash
$ ocean demo stream
▸ [event: task-start] PM Youngsu 가 Research 에이전트를 호출합니다...
▸ [event: invoke]      agent=Research duration=1.2s
▸ [event: complete]    팀 구성 완료: 3명
```

**S5 — 스펙 드리프트 자동 감지 (CI)**
```bash
$ ocean --offline agents list      # 캐시 사용
$ ocean --refresh-spec describe agents list  # CI에서 주기적으로
```

---

## 3. 기능 요구사항

### F-01: 스펙 로딩 (Spec Loader)

- **F-01-1**: 첫 실행 시 `GET {base_url}/openapi.json` 호출
- **F-01-2**: `~/.cache/ocean-cli/openapi.json` 에 저장, TTL 24시간
- **F-01-3**: `--refresh-spec` 플래그로 강제 갱신
- **F-01-4**: `--offline` 시 캐시만 사용, 네트워크 접근 금지
- **F-01-5**: `--spec <path|url>` 로 override 지원
- **F-01-6**: OpenAPI 3.0/3.1 모두 수용 (FastAPI 기본 3.1)

### F-02: 동적 커맨드 바인딩 (Binder)

- **F-02-1**: `operation.tags[0]` → 그룹 (없으면 path 첫 세그먼트)
- **F-02-2**: `operationId`를 snake_case → Typer command 이름
- **F-02-3**: 동일 그룹 내 이름 충돌 시 method 접미사 자동 추가
- **F-02-4**: `paths` 전체를 순회해 21개 이상 operation을 빠짐없이 등록
- **F-02-5**: 각 커맨드의 `--help` 는 OpenAPI `summary`/`description` 반영

### F-03: 파라미터 바인딩

- **F-03-1**: path param → 필수 positional argument
- **F-03-2**: query param → `--name value` 옵션 (required 보존)
- **F-03-3**: bool query → `--flag/--no-flag`
- **F-03-4**: array query → `--name val1 --name val2` (반복)
- **F-03-5**: enum → 허용 값 제한 (Typer Choice)
- **F-03-6**: request body → `--body '<json>'` 또는 `--body-file <path>`
- **F-03-7**: body 편의 입력 → `--field key=value` 반복 (top-level 필드만)
- **F-03-8**: `caller_agent_id` 필드는 `--as` / `OCEAN_CALLER_AGENT_ID` 에서 자동 주입

### F-04: 요청 실행

- **F-04-1**: httpx 기반 동기 클라이언트, 기본 timeout 30초
- **F-04-2**: `--base-url` 및 `OCEAN_API_BASE` 환경변수 (기본 `http://127.0.0.1:8000`)
- **F-04-3**: 3xx follow redirects 기본 활성화
- **F-04-4**: `--dry-run` 시 실제 요청 대신 equivalent `curl` 명령 출력
- **F-04-5**: `--verbose` 시 요청/응답 헤더 출력 (body는 포맷 규칙 동일)

### F-05: 출력 포맷

- **F-05-1**: 기본은 Rich 렌더러
  - 배열 → Table (컬럼 자동, 최대 8개)
  - 객체 → Panel + key/value 그리드
  - 스칼라 → 단순 출력
- **F-05-2**: `--format {rich,json,yaml,raw}` 전역 옵션
- **F-05-3**: `-q/--quiet` → JSON 한 줄 (파이프 용)
- **F-05-4**: `NO_COLOR` / `--no-color` 존중
- **F-05-5**: non-TTY 감지 시 자동으로 json 포맷으로 전환

### F-06: SSE 처리

- **F-06-1**: `Content-Type: text/event-stream` 응답 자동 감지
- **F-06-2**: event 블록 파싱 후 Rich Live 영역에 렌더
- **F-06-3**: `--raw` 시 원본 텍스트 그대로 출력
- **F-06-4**: `Ctrl+C` 로 깔끔 종료 (exit code 130)
- **F-06-5**: `--max-events N` / `--timeout N` 으로 종료 조건 제어

### F-07: 에러 처리

- **F-07-1**: 4xx → exit 1, 서버 메시지 Panel 출력
- **F-07-2**: 5xx → exit 2
- **F-07-3**: 네트워크 실패 → exit 3 + 백엔드 기동 힌트 (`uv run uvicorn ...`)
- **F-07-4**: 스펙 파싱 실패 → exit 4 + `--refresh-spec` 안내
- **F-07-5**: 입력 검증 실패 → exit 5 (Typer 기본)

### F-08: 부가 커맨드

- **F-08-1**: `ocean describe <group> <command>` — 파라미터/스키마 요약
- **F-08-2**: `ocean raw <METHOD> <PATH>` — 바인딩 우회 호출
- **F-08-3**: `ocean spec show` — 현재 스펙 소스/해시/TTL 출력
- **F-08-4**: `ocean --install-completion {bash,zsh,fish}` — 셸 자동완성 설치

### F-09: 패키징 & 실행

- **F-09-1**: 레포 루트 `cli/` 디렉토리
- **F-09-2**: `pyproject.toml`에 `[project.scripts] ocean = "cli.app:main"` 등록
- **F-09-3**: `uv run ocean ...` 로 실행 가능
- **F-09-4**: `python -m cli` 도 동일하게 동작

### F-10: 헬프 텍스트 품질 (Plain English)

> 핵심 원칙: **모든 `--help` 출력은 개발자가 아닌 사람이 읽어도 이해할 수 있는 평이한 영어로 작성한다.**

OpenAPI 원본의 `summary`/`description` 은 `List Agents`, `Create Agent` 같은 기계적 문구거나, 한국어와 영어가 섞여 있거나, 내부 구현 용어(`OrchestratorConfig`, `SSE`, `handler`)를 그대로 노출한다. CLI는 비개발자·데모 관객·초심 사용자에게도 노출되므로 이 텍스트를 **명시적으로 재작성한 사전(catalog)** 으로 덮어쓴다.

- **F-10-1**: CLI 안에 `cli/help_catalog.py` 또는 동등한 자료구조로 operationId → `{short, long, examples}` 매핑을 보유한다.
- **F-10-2**: Typer 커맨드 등록 시 OpenAPI `summary`/`description` 대신 이 카탈로그를 우선 사용한다. 카탈로그에 매핑이 없는 경우에만 원본을 fallback으로 쓰되, 개발 중 경고(`stderr`)를 내보낸다.
- **F-10-3**: 작성 규칙(스타일 가이드):
  - **언어**: 영어. 한국어/영어 혼용 금지.
  - **문체**: 능동태·현재형·2~3문장. 첫 문장은 "이 커맨드가 무엇을 하는가" 한 줄.
  - **어휘**: 개발 용어(`payload`, `endpoint`, `router`, `webhook handler`, `SSE`, `operationId`) 대신 쉬운 표현(`the data you send`, `the URL`, `live updates`) 사용.
  - **이니셜리즘 전개**: `SSE`, `CRUD`, `UUID` 같은 약어는 처음 등장 시 풀어서 쓰거나 풀이 추가 (`a stream of live updates (SSE)`).
  - **약속/한계**: 되돌릴 수 없는 동작(예: `teams delete`)은 help의 첫 문장 또는 두 번째 문장에서 "This cannot be undone." 같은 경고를 포함.
  - **예시 포함**: 각 커맨드마다 최소 1개의 실행 예시를 `--help` 하단 `Examples:` 블록으로 표시.
- **F-10-4**: 옵션/인자 설명도 같은 규칙을 따른다. `agent_id` 는 `The agent's unique ID. You can find it with "ocean agents list".` 처럼 "어디서 얻는지" 까지 알려준다.
- **F-10-5**: 루트 `--help` 는 제품 한 줄 소개("Talk to the AgentLinkedIn backend from your terminal.") + 대표 시나리오 3개 + `ocean <group> --help` 로 연결되는 그룹 목록을 보여준다.
- **F-10-6**: `ocean describe <group> <command>` 는 help보다 더 상세한 버전(파라미터 전체, 요청/응답 예시 JSON)을 제공한다.

### F-11: 전체 엔드포인트 커버리지 (No endpoint left behind)

> OpenAPI가 공개하는 모든 operation은 CLI에서 호출할 수 있어야 한다.

현재 스펙의 **21개 operation** 전부가 CLI 커맨드로 노출된다. 다음 표는 1:1 매핑 계약으로, 스펙이 확장될 때 이 표도 함께 갱신한다.

| # | Method | Path | CLI 커맨드 | 한 줄 헬프 (plain English) |
|---|---|---|---|---|
| 1 | GET | `/healthz` | `ocean health` | Quick check that the server is running. Replies in under a second. |
| 2 | GET | `/api/admin/health` | `ocean admin health` | Show backend status and how many agents, publishers, and teams exist. |
| 3 | GET | `/api/agents` | `ocean agents list` | List every registered agent with their trust score and verification badge. |
| 4 | POST | `/api/agents` | `ocean agents create` | Register a new agent. You provide the name, description, and owner info. |
| 5 | GET | `/api/agents/search` | `ocean agents search` | Find agents by keyword or tag, ranked by a weighted trust score. |
| 6 | GET | `/api/agents/{agent_id}` | `ocean agents get` | Show the full profile of one agent. |
| 7 | PATCH | `/api/agents/{agent_id}` | `ocean agents update` | Change parts of an agent's profile. Only the fields you pass are updated. |
| 8 | GET | `/api/agents/{agent_id}/stats` | `ocean agents stats` | Show how often an agent has been called and how reliable it has been. |
| 9 | GET | `/api/agents/{agent_id}/threads` | `ocean agents threads` | List conversation threads this agent has taken part in. |
| 10 | GET | `/api/publishers` | `ocean publishers list` | List every publisher and whether their identity is verified. |
| 11 | POST | `/api/publishers` | `ocean publishers create` | Register a new publisher. New publishers start as unverified. |
| 12 | GET | `/api/publishers/{publisher_id}` | `ocean publishers get` | Show one publisher's profile. |
| 13 | POST | `/api/publishers/{publisher_id}/verify` | `ocean publishers verify` | Grant the verified badge to a publisher. You can attach a short evidence note. |
| 14 | POST | `/api/publishers/{publisher_id}/unverify` | `ocean publishers unverify` | Remove a publisher's verified badge. |
| 15 | GET | `/api/threads/{thread_id}` | `ocean threads get` | Show one conversation thread and all its messages. |
| 16 | GET | `/api/teams` | `ocean teams list` | List every team that has been assembled. |
| 17 | DELETE | `/api/teams/{team_id}` | `ocean teams delete` | Delete a team. This cannot be undone. |
| 18 | POST | `/api/orchestrator/upload` | `ocean orchestrator upload` | Upload a Python template to start a new orchestrator session. |
| 19 | GET | `/api/orchestrator/template` | `ocean orchestrator template` | Download the Python template so you can customize your own orchestrator. |
| 20 | POST | `/api/github/webhook` | `ocean github webhook` | Send a test GitHub webhook event to the backend (for local testing). |
| 21 | GET | `/api/demo/stream` | `ocean demo stream` | Watch the orchestrator demo live. Shows each step as the team is assembled. |

- **F-11-1**: `ocean --help` 실행 시 위 커맨드가 모두 도달 가능해야 한다.
- **F-11-2**: `ocean describe` 는 21개 operation 모두에 대해 비어 있지 않은 정보를 반환해야 한다.
- **F-11-3**: 스펙에 추가된 새 operation은 자동으로 노출된다(동적 바인딩). 단, 새 operation은 help 카탈로그가 없으면 빌드 시 경고를 내어 사람이 카탈로그를 갱신하도록 유도한다.

---

## 4. 비기능 요구사항

| 항목 | 목표 |
|---|---|
| 첫 실행 시간 | < 1.5초 (캐시 없음 기준, 로컬 백엔드) |
| 캐시 사용 시 | < 300ms (command lookup + dispatch) |
| 의존성 | typer, rich, httpx, pyyaml (pytest는 dev) |
| Python 버전 | 3.12+ (레포 정책과 일치) |
| 테스트 커버리지 | binder/formatter/sse 80% 이상 |
| 문서화 | README + `--help` + `describe` |

---

## 5. 범위 밖 (Out of Scope)

- 쓰기 전용 스크립트 재생 (예: `ocean run scenario.yaml`) → 후속
- MCP 서버(`:8100`) 클라이언트 → 별도 도구 (`agents/agent_pm.py`)가 담당
- 인증/로그인 플로우 → CLAUDE.md 규칙상 불필요
- 서버 관리 명령(`start`, `stop`) → CLI는 순수 HTTP 클라이언트

---

## 6. 성공 기준

1. `ocean --help` 에 `agents/publishers/threads/teams/orchestrator/github/demo/admin` 8개 그룹 + 최상위 `health` 커맨드가 노출된다.
2. OpenAPI에 명시된 **21개 operation 전부**가 F-11 매핑 표대로 CLI에서 호출 가능하다.
3. `TEST_CASE_CLI.md` 의 모든 테스트 케이스가 통과한다. 특히 §12 "Per-Endpoint Coverage" 21개 테스트는 필수.
4. 백엔드에 새 엔드포인트를 추가하고 서버를 재시작하면, `--refresh-spec` 한 번으로 새 커맨드가 나타난다.
5. `ocean demo stream` 으로 SSE 이벤트가 실시간 렌더된다.
6. **헬프 품질 검사**: 21개 커맨드 각각의 `--help` 가 (a) 영어로만 작성되어 있고, (b) 최소 1개의 `Examples:` 블록을 포함하며, (c) 금지된 내부 용어(후술) 를 포함하지 않는다.

---

## 7. 의존성 및 선결 과제

- 백엔드 `:8000` 기동 가능 상태 (오늘 복구 완료 — `git restore .` 로 missing routers 복원)
- `backend/app/services/` 의 ` 2.py` untracked 파일은 CLI 작업과 독립, 추후 정리
- `pyproject.toml` 에 런타임 의존성 추가 필요: `typer>=0.12`, `rich>=13`, `httpx>=0.27`, `PyYAML>=6`

---

## 8. 용어

| 용어 | 정의 |
|---|---|
| spec | OpenAPI 3.x JSON (백엔드 `/openapi.json` 응답) |
| operation | OpenAPI에서 method+path 조합 (1개 = CLI 커맨드 1개) |
| group | CLI 최상위 그룹, 기본 `tags[0]` |
| caller_agent_id | AgentLinkedIn의 호출자 UUID, CLI는 `--as` 로 주입 |
