# plan.md — AgentLinkedIn CLI 구현 계획

> 백엔드 `openapi.json`을 소비해 모든 REST 엔드포인트를 터미널에서 호출할 수 있는 Python CLI (`ocean`) 구축 계획

---

## 0. 목표 요약

- FastAPI 백엔드(`http://127.0.0.1:8000`)의 모든 엔드포인트를 `ocean <group> <command>` 형태로 호출
- openapi.json을 **런타임**에 읽어 서브커맨드를 동적으로 구성 (정적 codegen 아님)
- 레포 내부 `cli/` 디렉토리에 거주, `uv run ocean` 으로 실행
- 인증 없음 (CLAUDE.md 규칙) — `caller_agent_id`만 필요 시 주입

---

## 1. 인터뷰 결과

| 항목 | 결정 |
|---|---|
| 언어/프레임워크 | **Python 3.12+ + Typer + Rich + httpx** |
| 코드 위치 | 레포 내 `cli/` 신규 디렉토리 |
| 엔드포인트 범위 | 전체 21개 operation 자동 매핑 |
| 인증 | 없음 (스펙 securitySchemes 비어 있음 확인) |

---

## 2. 확인된 OpenAPI 스펙 요약

- `info.title`: **AgentLinkedIn**
- `paths`: **18개 path / 21개 operation**
- 그룹(tag 기준):
  - `agents` — 7개 (CRUD, search, stats, threads)
  - `publishers` — 5개 (CRUD, verify/unverify)
  - `threads` — 1개 (상세)
  - `teams` — 2개 (목록, 삭제)
  - `orchestrator` — 2개 (upload, template)
  - `github` — 1개 (webhook)
  - `demo` — 1개 (SSE stream)
  - `admin` — 1개 (health)
  - 기타: `/healthz`
- SSE 엔드포인트 있음 → 스트리밍 전용 핸들러 필요

---

## 3. 런타임 전략: 동적 바인딩

### 3-1. 이유

- 백엔드에 엔드포인트가 추가되어도 CLI 재배포 불필요
- openapi.json 한 번만 파싱하면 Typer command tree 전체 구성 가능
- FastAPI가 스펙을 항상 최신으로 유지해 주므로 drift 없음

### 3-2. 캐시 정책

- 최초 실행 시 `GET /openapi.json` → `~/.cache/ocean-cli/openapi.json`에 저장
- TTL 24시간, 만료 시 자동 refetch
- `--refresh-spec` 플래그로 강제 갱신
- `--offline` 은 캐시만 사용 (네트워크 실패 허용)
- `--spec <path|url>` 로 override 가능 (테스트용)

---

## 4. 디렉토리 구조

```
cli/
├── __init__.py
├── __main__.py             # python -m cli 진입
├── app.py                  # Typer 루트 앱 + dynamic registration
├── spec_loader.py          # openapi.json fetch / cache / validate
├── binder.py               # OpenAPI operation → Typer command 변환
├── client.py               # httpx.Client 래퍼 (타임아웃, 에러 처리)
├── sse.py                  # text/event-stream 스트리밍
├── formatter.py            # Rich table / json / yaml 렌더러
├── config.py               # 환경변수, 캐시 경로 관리
├── errors.py               # exit code 및 에러 포맷
└── tests/
    ├── fixtures/
    │   └── mini_openapi.json
    ├── test_binder.py
    ├── test_formatter.py
    └── test_e2e.py         # TestClient 기반 왕복
```

---

## 5. 커맨드 네이밍 규칙

- **그룹**: `operation.tags[0]` → 없으면 path 첫 세그먼트 (`/api/agents/...` → `agents`)
- **커맨드**: `operationId`를 snake_case로 변환
  - 예: `list_agents` → `ocean agents list`
  - 예: `get_agent_stats` → `ocean agents get-stats`
- **충돌 해결**: 동일 그룹 내 중복 시 HTTP method 접미사 (`list-get`, `list-post`)

### 5-1. 매핑 예시

| OpenAPI | CLI 커맨드 |
|---|---|
| `GET /api/agents` | `ocean agents list` |
| `POST /api/agents` | `ocean agents create` |
| `GET /api/agents/{agent_id}` | `ocean agents get <AGENT_ID>` |
| `GET /api/agents/search?q=...` | `ocean agents search --q ...` |
| `GET /api/agents/{agent_id}/stats` | `ocean agents stats <AGENT_ID>` |
| `POST /api/publishers/{id}/verify` | `ocean publishers verify <PUBLISHER_ID>` |
| `GET /api/demo/stream` | `ocean demo stream` (SSE 전용) |
| `POST /api/orchestrator/upload` | `ocean orchestrator upload --body-file plan.json` |

---

## 6. 파라미터 바인딩 규칙

| OpenAPI 위치 | CLI 표현 |
|---|---|
| `path` | 필수 positional argument (`<AGENT_ID>`) |
| `query` 단일 | `--name value` 또는 `--flag/--no-flag` (bool) |
| `query` 배열 | `--tag a --tag b` (반복 허용) |
| `header` | `-H key=value` (일반) 또는 전용 옵션 |
| `requestBody` (application/json) | `--body '<json>'` 또는 `--body-file <path>` |
| `requestBody` 편의 | `--field key=value` 반복 (스키마 기반 자동 캐스팅) |

- enum → Typer `click.Choice`
- required 여부는 OpenAPI 스펙 그대로 반영
- 타입 캐스팅: integer/number/boolean/string/array

---

## 7. 출력 포맷

- 기본: Rich 렌더러
  - 배열 응답 → Table (컬럼은 첫 객체의 키 기준, 최대 8개, 나머지는 `--format json`)
  - 객체 응답 → Panel + key/value
- `--format json` / `--format yaml` / `--format raw`
- `-q/--quiet` : JSON만 출력 (파이프용)
- 컬러: `NO_COLOR` env 또는 `--no-color` 존중

---

## 8. SSE 처리

- `response.headers.content-type`이 `text/event-stream`이면 전용 경로
- `httpx.Client.stream()` → 라인 단위 파싱 → `event:` / `data:` 분리
- Rich Live 영역에 흐르도록 출력, `Ctrl+C`로 깔끔 종료
- `--raw` 옵션이면 원본 텍스트 그대로 출력 (파이프 친화)

---

## 9. 에러 처리 & Exit Code

| 상황 | Exit Code | 동작 |
|---|---|---|
| 성공 (2xx) | 0 | 정상 출력 |
| 사용자 실수 (4xx) | 1 | Rich Panel로 status + 서버 메시지 |
| 서버 오류 (5xx) | 2 | 동일 + stderr 경고 |
| 네트워크 실패 | 3 | `Connection refused` 안내 + 서버 기동 힌트 |
| 스펙 파싱 실패 | 4 | 캐시 무효화 안내 |
| 사용자 입력 검증 실패 | 5 | Typer 기본 에러 |

---

## 10. 전역 옵션

```
ocean [GLOBAL OPTIONS] <group> <command> [ARGS]

GLOBAL OPTIONS:
  --base-url URL            기본 http://127.0.0.1:8000 (env: OCEAN_API_BASE)
  --as AGENT_ID             caller_agent_id 자동 주입 (env: OCEAN_CALLER_AGENT_ID)
  --format {rich,json,yaml,raw}
  --spec PATH|URL           스펙 override
  --refresh-spec            캐시 무효화
  --offline                 네트워크 차단, 캐시만
  --timeout SECONDS         기본 30
  --dry-run                 요청 대신 equivalent curl 출력
  --verbose / -v            요청/응답 헤더까지 출력
  --no-color
```

---

## 11. 부가 기능

- `ocean describe <group> <command>` — 해당 operation의 스펙 요약 (paramters, requestBody schema, responses)
- `ocean raw <METHOD> <PATH> [--body ... --query k=v]` — 바인딩 우회, 임의 경로 호출
- `ocean --install-completion {bash,zsh,fish}` — Typer 내장
- `ocean spec show` — 현재 사용 중인 스펙 파일 위치/해시 출력

---

## 12. 마일스톤

| # | 목표 | 산출물 |
|---|---|---|
| **M1** | 스펙 로더 + httpx 클라이언트 + `ocean raw` | 네트워크 왕복 검증, 에러 처리 골격 |
| **M2** | binder로 전체 엔드포인트 자동 매핑 + JSON 포맷 | 21개 operation 모두 호출 가능 |
| **M3** | Rich 렌더러 + SSE + `describe` + `dry-run` | DX 완성 |
| **M4** | 테스트 + pyproject scripts + README + 셸 자동완성 | `uv run ocean` 배포 가능 |

---

## 13. 스케줄 (대략)

- M1: 0.5일
- M2: 1일
- M3: 1일
- M4: 0.5일

합계 ≈ **3일** (1인 기준)

---

## 14. 위험 요소 및 대응

| 위험 | 대응 |
|---|---|
| OpenAPI operationId 충돌 | method 접미사로 자동 중복 해소 |
| 중첩 객체 requestBody 표현이 모호 | `--body-file` 우선, `--field` 는 top-level만 |
| SSE 렌더링이 CI에서 hang | `--no-stream` (한 번 받고 exit) + timeout |
| 파이썬 3.14 런타임 호환 (uv 기본) | httpx/typer/rich 모두 지원 확인됨 |
| `caller_agent_id`가 path에 들어있지 body에 있는 경우 혼재 | 파라미터 이름 휴리스틱 (`caller_agent_id`) 로 자동 매핑 |

---

## 15. 선결 과제 (레포 이슈)

- `backend/app/routers/` 내 일부 파일이 macOS clone 과정에서 파일명 충돌로 손상되어 있었음 → `git restore .` 로 복원 완료
- `backend/app/services/` 에도 ` 2.py` 형태의 중복 파일이 untracked로 남아 있음 → CLI 작업 완료 후 정리 권장

---

## 16. 승인 후 다음 단계

1. `cli/` 스캐폴딩 (M1)
2. 첫 왕복 검증: `ocean raw GET /healthz`
3. M2 풀 바인딩 진입

---

## 17. 문서 개정 요약 (2026-04-20)

- **F-10 헬프 품질** 추가: 모든 `--help` 출력은 plain English, 비개발자 독해 가능. `cli/help_catalog.py` 로 관리.
- **F-11 전체 커버리지** 추가: 21개 operation 모두 CLI 커맨드로 노출 (누락 금지).
- TSD §4-8, §4-9, §10-1, §10-2 신설: HelpCatalog 자료구조, 엔드포인트 명세표, 린터 규칙.
- TEST_CASE §12 Per-Endpoint Coverage 21개 + §13 헬프 품질 10개 케이스 신설.
- `/healthz` 는 최상위 `ocean health` 로 매핑 (tag 없는 operation 처리 규칙).
- DELETE(`teams delete`) 는 `HelpEntry.warnings` + TTY 확인 프롬프트 필수.
