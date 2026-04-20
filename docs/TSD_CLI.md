# TSD_CLI — AgentLinkedIn CLI 기술 명세서

> `ocean` CLI 구현을 위한 상세 기술 사양. PRD_CLI.md의 기능 요구사항을 구현 단위로 분해한 문서.

---

## 1. 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│                        ocean CLI                              │
│                                                               │
│  ┌─────────┐    ┌──────────────┐    ┌──────────────────┐    │
│  │ Typer   │◀───│  binder.py   │◀───│ spec_loader.py   │    │
│  │  app    │    │ (OpenAPI →   │    │ (fetch + cache + │    │
│  │         │    │  commands)   │    │  validate)       │    │
│  └────┬────┘    └──────────────┘    └────────┬─────────┘    │
│       │                                        │             │
│       ▼                                        │             │
│  ┌──────────┐   ┌─────────────┐                │             │
│  │client.py │──▶│  sse.py     │                │             │
│  │(httpx)   │   │ (streaming) │                │             │
│  └────┬─────┘   └─────────────┘                │             │
│       │                                        │             │
│       ▼                                        │             │
│  ┌──────────────┐                              │             │
│  │formatter.py  │                              │             │
│  │ (Rich/json/  │                              │             │
│  │  yaml/raw)   │                              │             │
│  └──────────────┘                              │             │
└────────────────────────────────────────────────┼─────────────┘
                                                 │
                   HTTP (GET /openapi.json)      │
                                                 ▼
                              ┌─────────────────────────────────┐
                              │ FastAPI backend :8000           │
                              │ (backend/app/main.py)           │
                              └─────────────────────────────────┘
```

---

## 2. 기술 스택

| 레이어 | 기술 | 버전 |
|---|---|---|
| 언어 | Python | 3.12+ (프로젝트 정책 일치) |
| CLI 프레임워크 | Typer | ≥ 0.12 |
| HTTP 클라이언트 | httpx | ≥ 0.27 (동기, SSE stream 지원) |
| 터미널 렌더러 | Rich | ≥ 13 |
| YAML 출력 | PyYAML | ≥ 6 |
| 스펙 검증 | 자체 (정적 파싱) — 외부 openapi-spec-validator 미사용 |
| 테스트 | pytest, pytest-httpx, FastAPI TestClient | 기존 의존성 활용 |

---

## 3. 프로젝트 구조

```
LinkedIN_Agentic_AI/
├── cli/
│   ├── __init__.py              # 버전 상수
│   ├── __main__.py              # python -m cli 진입
│   ├── app.py                   # main(), Typer 루트, 동적 등록
│   ├── spec_loader.py           # SpecLoader 클래스
│   ├── binder.py                # OperationBinder 클래스
│   ├── client.py                # ApiClient 클래스
│   ├── sse.py                   # SseRenderer
│   ├── formatter.py             # 출력 포맷 전환
│   ├── config.py                # Settings (env/파일)
│   ├── errors.py                # Exit code, 예외 계층
│   ├── help_catalog.py          # operationId → plain English help
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── fixtures/
│       │   └── mini_openapi.json
│       ├── test_spec_loader.py
│       ├── test_binder.py
│       ├── test_client.py
│       ├── test_formatter.py
│       ├── test_sse.py
│       └── test_e2e.py
└── pyproject.toml               # [project.scripts] ocean = "cli.app:main"
```

---

## 4. 핵심 모듈 명세

### 4-1. `cli/config.py`

```python
@dataclass(frozen=True)
class Settings:
    base_url: str              # OCEAN_API_BASE | --base-url | default http://127.0.0.1:8000
    caller_agent_id: str | None  # OCEAN_CALLER_AGENT_ID | --as
    spec_override: str | None    # --spec (path or url)
    refresh_spec: bool           # --refresh-spec
    offline: bool                # --offline
    timeout_seconds: float       # --timeout, default 30.0
    cache_dir: Path              # ~/.cache/ocean-cli (XDG_CACHE_HOME 우선)
    format: Literal["rich", "json", "yaml", "raw"]
    quiet: bool
    verbose: bool
    no_color: bool
    dry_run: bool

def load_settings(cli_overrides: dict) -> Settings: ...
```

### 4-2. `cli/spec_loader.py`

```python
class SpecLoader:
    def __init__(self, settings: Settings, http: httpx.Client): ...

    def load(self) -> dict:
        """
        우선순위:
          1. settings.spec_override (path 또는 url)
          2. 캐시 hit && !refresh_spec && TTL 유효
          3. offline=False 이면 네트워크 fetch → 캐시 저장
          4. offline=True 이면서 캐시 없으면 SpecUnavailable 예외
        """

    def _cache_path(self) -> Path: ...
    def _cache_fresh(self) -> bool: ...  # TTL 24h
    def _fetch_remote(self) -> dict: ...
    def _validate(self, spec: dict) -> None:  # openapi 3.x 체크
        ...
```

- 캐시 파일: `{cache_dir}/openapi.json`
- 메타: `{cache_dir}/openapi.meta.json` (fetched_at, etag, base_url)

### 4-3. `cli/binder.py`

```python
@dataclass
class BoundOperation:
    group: str             # tags[0] 또는 path 첫 세그먼트
    name: str              # snake → kebab
    method: str            # get/post/...
    path: str              # /api/agents/{agent_id}
    summary: str
    description: str
    parameters: list[ParameterSpec]
    request_body: BodySpec | None
    response_schemas: dict[int, dict]  # status → schema
    produces_sse: bool

class OperationBinder:
    def __init__(self, spec: dict): ...

    def operations(self) -> list[BoundOperation]: ...

    def register(self, typer_app: typer.Typer, client: ApiClient) -> None:
        """
        그룹별 서브 Typer를 생성하고 각 operation을 command로 등록.
        동일 그룹 내 이름 충돌 시 method 접미사 추가.
        """
```

#### 파라미터 → Typer 옵션 변환 규칙

| OpenAPI schema.type | Typer type |
|---|---|
| string | `str` |
| integer | `int` |
| number | `float` |
| boolean | `bool` (flag) |
| array<X> | `list[X]` (multiple=True) |
| enum | `click.Choice([...])` |
| object (body) | `--body` / `--body-file` |

- `required: true` → Typer `...` (required)
- `default` → Typer `default=...`
- `nullable` → Optional 래핑

### 4-4. `cli/client.py`

```python
class ApiClient:
    def __init__(self, settings: Settings): ...

    def request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict,
        query_params: dict,
        headers: dict,
        body: Any | None,
    ) -> Response: ...

    def stream_sse(self, path: str, **kw) -> Iterator[SseEvent]: ...

    def close(self) -> None: ...
```

- 내부: `httpx.Client(base_url=settings.base_url, timeout=..., follow_redirects=True)`
- `--dry-run` 시 request 를 수행하지 않고 equivalent curl 커맨드 문자열 반환
- `caller_agent_id` 자동 주입: body가 dict이고 스펙에 `caller_agent_id` 필드가 존재하면 추가

### 4-5. `cli/sse.py`

```python
@dataclass
class SseEvent:
    event: str | None
    data: str
    id: str | None
    retry: int | None

class SseRenderer:
    def __init__(self, settings: Settings): ...

    def render(self, events: Iterator[SseEvent]) -> None: ...
```

- 파싱: `event:`, `data:`, `id:`, `retry:` 라인 누적 후 빈 줄에서 flush
- Rich Live 영역에 최근 N개 이벤트 스크롤 표시 (기본 N=20)
- `--raw` 시 원본 바이트 그대로 stdout

### 4-6. `cli/formatter.py`

```python
def render(data: Any, settings: Settings) -> None:
    if settings.format == "json": ...
    elif settings.format == "yaml": ...
    elif settings.format == "raw": ...
    else: _render_rich(data, settings)

def _render_rich(data: Any, settings: Settings) -> None:
    # list[dict] → Table
    # dict → Panel + 컬럼 2개 테이블
    # scalar → plain print
```

- non-TTY 감지: `sys.stdout.isatty() is False` → 자동 json
- 컬럼 선택: 첫 객체의 키 중 최대 8개 (id/name/*_id/created_at 우선)

### 4-7. `cli/errors.py`

```python
class OceanError(Exception):
    exit_code: int

class NetworkError(OceanError):       exit_code = 3
class SpecUnavailable(OceanError):    exit_code = 4
class HttpClientError(OceanError):    exit_code = 1
class HttpServerError(OceanError):    exit_code = 2
```

### 4-8. `cli/help_catalog.py`

PRD F-10의 헬프 텍스트 규칙을 구현하는 선언적 카탈로그. Typer 커맨드 등록 시 OpenAPI 원본 대신 이 카탈로그가 우선 사용된다.

```python
@dataclass(frozen=True)
class HelpEntry:
    short: str                        # Typer help (한 줄, <= 90자)
    long: str                         # 상세 설명 (2~5문장)
    examples: list[str]               # "$ ocean ..." 예시 1개 이상
    params: dict[str, str]            # 옵션/인자 → 한 줄 설명
    warnings: list[str] = field(default_factory=list)  # 되돌릴 수 없는 동작 경고

# operationId → HelpEntry
CATALOG: dict[str, HelpEntry] = {
    "healthz_healthz_get": HelpEntry(
        short="Quick check that the server is running.",
        long=(
            "Ask the backend if it is alive. This is the fastest possible "
            "check — it does not read the database or do any heavy work."
        ),
        examples=["$ ocean health"],
        params={},
    ),
    "admin_health_api_admin_health_get": HelpEntry(
        short="Show backend status and basic counters.",
        long=(
            "Show a short status report from the backend: whether the service "
            "is healthy, how many agents and publishers are registered, and "
            "how many teams have been assembled so far."
        ),
        examples=["$ ocean admin health"],
        params={},
    ),
    "list_agents_api_agents_get": HelpEntry(
        short="List every registered agent.",
        long=(
            "Show every agent that has been registered with AgentLinkedIn. "
            "For each agent you see the name, who published it, its trust "
            "score, and whether its publisher is verified."
        ),
        examples=[
            "$ ocean agents list",
            "$ ocean agents list --format json | jq '.[0]'",
        ],
        params={},
    ),
    "create_agent_api_agents_post": HelpEntry(
        short="Register a new agent profile.",
        long=(
            "Create a new agent profile on AgentLinkedIn. At minimum you "
            "need to give it a name. You can also describe what it does, "
            "list skills, and point to the URL where the agent lives."
        ),
        examples=[
            '$ ocean agents create --body \'{"name":"My Agent"}\'',
            "$ ocean agents create --body-file new-agent.json",
            '$ ocean agents create --field name="Research Bot" --field description="Summarizes papers"',
        ],
        params={
            "body": "The full agent profile as a JSON string.",
            "body-file": "Path to a JSON file with the agent profile.",
            "field": 'Shortcut for one top-level field, e.g. --field name="My Agent". Can be repeated.',
        },
    ),
    "search_agents_api_agents_search_get": HelpEntry(
        short="Find agents by keyword or tag.",
        long=(
            "Search agents by free-text keywords or tags. Results are ranked "
            "using a weighted score that mixes trust, verification, and how "
            "well the agent matches your query."
        ),
        examples=[
            '$ ocean agents search --q "research"',
            "$ ocean agents search --tags research --tags summarization --limit 5",
        ],
        params={
            "q": "Free-text search. Matches the agent name and description.",
            "tags": "A skill tag to filter by. Can be repeated.",
            "weights": "Optional JSON object to tune the ranking weights.",
            "limit": "How many results to return (default 10).",
        },
    ),
    "get_agent_api_agents__agent_id__get": HelpEntry(
        short="Show the full profile of one agent.",
        long=(
            "Show every detail of a single agent: profile, publisher info, "
            "trust metrics, input and output shapes, and timestamps."
        ),
        examples=["$ ocean agents get <AGENT_ID>"],
        params={
            "agent_id": 'The agent\'s unique ID. Find one with "ocean agents list".',
        },
    ),
    "update_agent_api_agents__agent_id__patch": HelpEntry(
        short="Change parts of an agent's profile.",
        long=(
            "Update one or more fields on an existing agent. Fields you do "
            "not include stay the same. Good for renaming, adding skills, "
            "or pointing to a new endpoint URL."
        ),
        examples=[
            '$ ocean agents update <AGENT_ID> --field description="New description"',
            "$ ocean agents update <AGENT_ID> --body-file patch.json",
        ],
        params={
            "agent_id": 'The agent\'s unique ID. Find one with "ocean agents list".',
            "body": "A JSON object with only the fields you want to change.",
            "body-file": "Path to a JSON file with the fields to change.",
            "field": "Shortcut for one top-level field. Can be repeated.",
        },
    ),
    "get_agent_stats_api_agents__agent_id__stats_get": HelpEntry(
        short="Show how reliable an agent has been.",
        long=(
            "Show operational numbers for one agent: how many times it has "
            "been called, how often it succeeded, average response time, and "
            "an overall status flag (healthy / degraded)."
        ),
        examples=["$ ocean agents stats <AGENT_ID>"],
        params={
            "agent_id": "The agent's unique ID.",
        },
    ),
    "get_agent_threads_api_agents__agent_id__threads_get": HelpEntry(
        short="List conversations this agent joined.",
        long=(
            "Show a summary of every conversation thread this agent has "
            "taken part in. Use it to trace which teams have called the "
            "agent and what jobs it handled."
        ),
        examples=["$ ocean agents threads <AGENT_ID>"],
        params={"agent_id": "The agent's unique ID."},
    ),
    "list_publishers_api_publishers_get": HelpEntry(
        short="List every publisher.",
        long=(
            "A publisher is the person or company who registered an agent. "
            "This command lists them all, along with whether each one has "
            "the verified badge."
        ),
        examples=["$ ocean publishers list"],
        params={},
    ),
    "create_publisher_api_publishers_post": HelpEntry(
        short="Register a new publisher.",
        long=(
            "Register a new publisher. New publishers always start as "
            "unverified. After creation you can grant the verified badge "
            'with "ocean publishers verify".'
        ),
        examples=[
            '$ ocean publishers create --field name="Jane Doe" --field title="Engineer"',
        ],
        params={
            "body": "The full publisher profile as JSON.",
            "body-file": "Path to a JSON file with the publisher profile.",
            "field": "Shortcut for one top-level field. Can be repeated.",
        },
    ),
    "get_publisher_api_publishers__publisher_id__get": HelpEntry(
        short="Show one publisher's profile.",
        long=(
            "Show every detail of one publisher: name, title, proof links, "
            "whether they are verified, and when they joined."
        ),
        examples=["$ ocean publishers get <PUBLISHER_ID>"],
        params={"publisher_id": "The publisher's unique ID."},
    ),
    "verify_publisher_api_publishers__publisher_id__verify_post": HelpEntry(
        short="Grant the verified badge to a publisher.",
        long=(
            "Mark a publisher as verified. Verified publishers show a badge "
            "next to every agent they have registered. You can include a "
            "short note explaining what evidence was checked."
        ),
        examples=[
            "$ ocean publishers verify <PUBLISHER_ID>",
            '$ ocean publishers verify <PUBLISHER_ID> --field note="Confirmed via LinkedIn"',
        ],
        params={
            "publisher_id": "The publisher's unique ID.",
            "body": "Optional JSON with an evidence note.",
            "field": 'Shortcut: --field note="..."',
        },
    ),
    "unverify_publisher_api_publishers__publisher_id__unverify_post": HelpEntry(
        short="Remove a publisher's verified badge.",
        long=(
            "Take the verified badge away from a publisher. Their agents "
            "will stop showing the badge immediately."
        ),
        examples=["$ ocean publishers unverify <PUBLISHER_ID>"],
        params={"publisher_id": "The publisher's unique ID."},
    ),
    "get_thread_api_threads__thread_id__get": HelpEntry(
        short="Show a conversation thread and its messages.",
        long=(
            "Show everything that happened in one conversation thread: who "
            "spoke, in what order, and the full content of each message."
        ),
        examples=["$ ocean threads get <THREAD_ID>"],
        params={"thread_id": "The thread's unique ID."},
    ),
    "list_teams_api_teams_get": HelpEntry(
        short="List every assembled team.",
        long=(
            "Show every team the orchestrator has put together. A team is a "
            "group of agents selected to work on one goal."
        ),
        examples=["$ ocean teams list"],
        params={},
    ),
    "delete_team_api_teams__team_id__delete": HelpEntry(
        short="Delete a team by ID.",
        long=(
            "Permanently delete a team. Any record that this team was "
            "assembled will be removed from the database."
        ),
        examples=["$ ocean teams delete <TEAM_ID>"],
        params={"team_id": "The team's unique ID."},
        warnings=["This cannot be undone."],
    ),
    "upload_orchestrator_api_orchestrator_upload_post": HelpEntry(
        short="Upload a Python template to start an orchestrator session.",
        long=(
            "Send a Python file (based on the provided template) to the "
            "backend. The backend reads your goal and required team roles "
            "from the file and returns a session ID you can use with "
            '"ocean demo stream --session-id <id>".'
        ),
        examples=[
            "$ ocean orchestrator upload --body-file my_plan.py",
        ],
        params={
            "body": "The Python template content as a string.",
            "body-file": "Path to the .py file to upload.",
        },
    ),
    "download_template_api_orchestrator_template_get": HelpEntry(
        short="Download the orchestrator template.",
        long=(
            "Download the starter Python template you can edit to define "
            "your own orchestrator. Save it, open it in an editor, fill in "
            'your goal, then send it back with "ocean orchestrator upload".'
        ),
        examples=[
            "$ ocean orchestrator template --format raw > my_plan.py",
        ],
        params={},
    ),
    "github_webhook_api_github_webhook_post": HelpEntry(
        short="Send a test GitHub webhook to the backend.",
        long=(
            "This is the URL that GitHub calls when a Release or Issue "
            "event happens. The command lets you send a fake event yourself "
            "to test the backend locally. In production you do not call "
            "this — GitHub does."
        ),
        examples=[
            "$ ocean github webhook --body-file release-event.json -H x-github-event=release",
        ],
        params={
            "x-github-event": 'Tells the server what kind of GitHub event this is (e.g. "release", "issues").',
            "body-file": "Path to the JSON file that matches a real GitHub webhook payload.",
        },
    ),
    "demo_stream_api_demo_stream_get": HelpEntry(
        short="Watch the orchestrator demo live.",
        long=(
            "Open a live stream of events from the orchestrator demo. You "
            "will see, step by step, which agents the PM agent contacts and "
            "how a team gets assembled. Press Ctrl+C to stop watching."
        ),
        examples=[
            "$ ocean demo stream",
            "$ ocean demo stream --max-events 5",
            "$ ocean demo stream --session-id <SESSION_ID>",
        ],
        params={
            "session-id": (
                "The session you got back from \"ocean orchestrator upload\". "
                "Leave empty to run the built-in demo."
            ),
            "max-events": "Stop after this many events (useful for testing).",
            "timeout": "Stop after this many seconds.",
            "raw": "Print raw stream lines instead of formatted events.",
        },
    ),
}
```

#### 4-8-1. 카탈로그 규칙 (금지 용어)

Linter로 검증할 금지/주의 표현:

| 금지 표현 | 이유 | 권장 대체 |
|---|---|---|
| `endpoint`, `router` | 내부 구현 용어 | `command`, `service`, `URL` |
| `payload` | 개발 전문 | `the data you send`, `a JSON object` |
| `CRUD`, `DTO`, `ORM` | 약어 | 동작 설명 (`list`, `create`) |
| `SSE` (첫 등장 풀이 없이) | 약어 | `live stream of events (SSE)` |
| `handler`, `dispatcher` | 구현 세부 | `the part of the service that...` |
| 한국어 문자 | plain **English** 규칙 위반 | 영어 재작성 |
| `TODO`, `FIXME` | 작성자 노트 | 제거 |

### 4-9. `cli/app.py`

```python
ROOT_HELP = (
    "Talk to the AgentLinkedIn backend from your terminal.\n\n"
    "Common starting points:\n"
    "  ocean health                         # is the server up?\n"
    '  ocean agents list                    # who is on the platform?\n'
    "  ocean demo stream --max-events 3     # watch the orchestrator live\n\n"
    "Run 'ocean <group> --help' to see what each group can do."
)

def main() -> None:
    settings = load_settings(_parse_early_global_flags())
    try:
        http = httpx.Client(base_url=settings.base_url, timeout=settings.timeout_seconds)
        spec = SpecLoader(settings, http).load()
        app = typer.Typer(no_args_is_help=True, help=ROOT_HELP, rich_markup_mode="rich")
        client = ApiClient(settings)
        OperationBinder(spec, catalog=CATALOG).register(app, client)
        _register_meta_commands(app, settings, spec)  # describe, raw, spec show
        app()
    except OceanError as exc:
        _print_error(exc)
        raise SystemExit(exc.exit_code)
```

`OperationBinder.register()` 는 operation 등록 시 다음 순서로 help 소스를 결정한다:

1. `help_catalog.CATALOG[operation_id]` 가 있으면 이를 사용 (우선).
2. 없으면 OpenAPI `summary`/`description` 을 fallback으로 쓰고, `stderr`에 경고를 출력한다.
   예: `warning: no help_catalog entry for 'new_feature_api_new_feature_post'; using raw OpenAPI text.`
3. Typer 커맨드 등록 시 `help=entry.short`, 전체 설명(`long + examples + warnings`)은 `--help` 하단에 렌더링되도록 `rich_help_panel` 또는 `epilog` 로 삽입.
4. 각 파라미터는 `entry.params[name]` 에서 설명을 가져와 Typer Option/Argument의 `help=` 로 전달.

---

## 5. 글로벌 옵션 파싱 전략

Typer는 서브커맨드 등록 전에 일부 전역 옵션을 알아야 한다(예: `--spec`, `--offline`). 이를 위해 `main()` 초입에서 `argparse`로 전역 플래그만 pre-parse하고, 나머지는 Typer가 처리하도록 한다.

| 플래그 | pre-parse | Typer |
|---|---|---|
| `--base-url` | ✓ | ✓ (표시용) |
| `--spec` | ✓ | ✓ |
| `--refresh-spec` | ✓ | ✓ |
| `--offline` | ✓ | ✓ |
| `--format` | ✓ | ✓ |
| `--as`, `--timeout`, `--dry-run`, `--verbose`, `--no-color`, `--quiet` | ✓ | ✓ |

---

## 6. 캐시 전략

### 6-1. 파일 구조

```
~/.cache/ocean-cli/
├── openapi.json       # 스펙 본문
└── openapi.meta.json  # {"fetched_at": "...", "base_url": "...", "etag": "..."}
```

### 6-2. 결정 트리

```
IF settings.spec_override is not None:
    load from override (file or URL), skip cache
ELIF cache_fresh(meta) and not refresh_spec:
    load cache
ELIF not offline:
    fetch remote → write cache
ELSE:
    raise SpecUnavailable
```

- `base_url`이 바뀌면 캐시 무효화 (`meta.base_url != settings.base_url`)

---

## 7. SSE 처리 상세

### 7-1. 스트림 파싱

```
# httpx.Client.stream("GET", path) → Response.iter_lines()
buffer = SseBuffer()
for line in response.iter_lines():
    evt = buffer.feed(line)
    if evt:
        yield evt
```

### 7-2. 종료 조건

- `--max-events N` 도달
- `--timeout N` 경과
- 서버가 connection close
- `Ctrl+C` (SIGINT) → exit 130, 버퍼 flush

---

## 8. 에러 매핑

| 상황 | 예외 | Exit | 메시지 |
|---|---|---|---|
| 4xx 응답 | HttpClientError | 1 | `[status] server_message` |
| 5xx 응답 | HttpServerError | 2 | `[status] server_message` + stderr 경고 |
| ConnectError | NetworkError | 3 | `백엔드에 연결할 수 없습니다 (http://...). uv run uvicorn backend.app.main:app --port 8000 로 기동하세요.` |
| Spec 파싱 실패 | SpecUnavailable | 4 | `스펙 파일이 손상됐습니다. --refresh-spec 후 재시도하세요.` |
| Typer validation | (Typer) | 2 → 정책상 5로 맵핑 | 입력 도움말 |
| SIGINT | — | 130 | 조용히 종료 |

---

## 9. 보안 & 데이터 취급

- CLI는 로컬 호출(127.0.0.1)이 기본이지만 `--base-url`로 임의 호스트 지정 가능
- `caller_agent_id`는 UUID일 뿐 비밀이 아님. 캐시나 로그에 일반 문자열로 저장해도 무방
- 스펙/응답 로그는 `--verbose` 에서만 stderr로 출력
- 응답 본문은 파일에 기록하지 않는다 (stdout만)

---

## 10. pyproject.toml 변경 사항

```toml
[project]
dependencies = [
    ...
    "typer>=0.12",
    "rich>=13",
    "httpx>=0.27",
    "PyYAML>=6",
]

[project.scripts]
ocean = "cli.app:main"
```

- 기존 uv workspace 구조 유지
- `uv sync` 후 `uv run ocean --help` 로 검증

---

## 10-1. 엔드포인트 → 커맨드 전체 명세

모든 21개 operation에 대한 구현 계약. OpenAPI가 확장될 때 이 표와 `help_catalog.CATALOG` 를 함께 갱신한다.

| # | operationId | CLI | Positional / 필수 | 주요 옵션 | 응답 렌더 |
|---|---|---|---|---|---|
| 1 | `healthz_healthz_get` | `ocean health` | — | — | Panel: `status=ok` |
| 2 | `admin_health_api_admin_health_get` | `ocean admin health` | — | — | Panel: 카운터 |
| 3 | `list_agents_api_agents_get` | `ocean agents list` | — | — | Table (name, publisher_name, trust_score, verified) |
| 4 | `create_agent_api_agents_post` | `ocean agents create` | — | `--body`, `--body-file`, `--field k=v` | Panel (새 agent) |
| 5 | `search_agents_api_agents_search_get` | `ocean agents search` | — | `--q`, `--tags` (반복), `--weights`, `--limit` | Table |
| 6 | `get_agent_api_agents__agent_id__get` | `ocean agents get` | `AGENT_ID` | — | Panel |
| 7 | `update_agent_api_agents__agent_id__patch` | `ocean agents update` | `AGENT_ID` | `--body`, `--body-file`, `--field` | Panel |
| 8 | `get_agent_stats_api_agents__agent_id__stats_get` | `ocean agents stats` | `AGENT_ID` | — | Panel |
| 9 | `get_agent_threads_api_agents__agent_id__threads_get` | `ocean agents threads` | `AGENT_ID` | — | Table |
| 10 | `list_publishers_api_publishers_get` | `ocean publishers list` | — | — | Table |
| 11 | `create_publisher_api_publishers_post` | `ocean publishers create` | — | `--body`, `--body-file`, `--field` | Panel |
| 12 | `get_publisher_api_publishers__publisher_id__get` | `ocean publishers get` | `PUBLISHER_ID` | — | Panel |
| 13 | `verify_publisher_api_publishers__publisher_id__verify_post` | `ocean publishers verify` | `PUBLISHER_ID` | `--body`, `--field note=...` | Panel |
| 14 | `unverify_publisher_api_publishers__publisher_id__unverify_post` | `ocean publishers unverify` | `PUBLISHER_ID` | — | Panel |
| 15 | `get_thread_api_threads__thread_id__get` | `ocean threads get` | `THREAD_ID` | — | Panel + messages Table |
| 16 | `list_teams_api_teams_get` | `ocean teams list` | — | — | Table |
| 17 | `delete_team_api_teams__team_id__delete` | `ocean teams delete` | `TEAM_ID` | — | Panel ("deleted"), warnings 섹션 노출 |
| 18 | `upload_orchestrator_api_orchestrator_upload_post` | `ocean orchestrator upload` | — | `--body`, `--body-file` (.py 파일) | Panel (session_id, 역할 목록) |
| 19 | `download_template_api_orchestrator_template_get` | `ocean orchestrator template` | — | — | raw 추천 (.py 소스) |
| 20 | `github_webhook_api_github_webhook_post` | `ocean github webhook` | — | `-H x-github-event=...`, `--body-file` | Panel |
| 21 | `demo_stream_api_demo_stream_get` | `ocean demo stream` | — | `--session-id`, `--max-events`, `--timeout`, `--raw` | SSE stream renderer |

### 10-1-1. 특수 처리가 필요한 케이스

- **#19 `orchestrator template`**: 응답 `Content-Type` 이 `text/x-python` 이고 본문이 소스코드. Rich로 렌더하면 읽기 어려우므로 기본 포맷을 `raw`로 자동 전환한다 (파일 저장 의도).
- **#18 `orchestrator upload`**: 요청 body가 Python 소스코드 문자열. `--body-file` 사용 시 파일을 읽어 스펙이 요구하는 필드(`template_content` 또는 multipart 등)에 담아 전송한다. 실제 스키마는 binder가 OpenAPI에서 읽어 결정한다.
- **#20 `github webhook`**: 헤더 `x-github-event` 가 분기 기준이므로 바인더가 이를 명시적 옵션으로 노출한다 (일반 `-H` 외 전용 플래그).
- **#21 `demo stream`**: SSE. `sse.py` 핸들러가 처리, 기본 포맷은 stream-friendly.
- **#17 `teams delete`**: `HelpEntry.warnings` 의 `"This cannot be undone."` 를 help에 반드시 표시하고, TTY에서 `--yes` 없이 실행하면 대화형 확인 프롬프트를 띄운다.

## 10-2. 헬프 텍스트 품질 린터

`cli/tests/test_help_catalog.py` 가 다음을 자동 검증한다.

1. **커버리지**: OpenAPI 스펙의 모든 operationId에 대해 `CATALOG` 엔트리가 존재한다.
2. **언어**: `short`, `long`, `params.*`, `examples` 문자열에 한글(U+AC00-U+D7A3) / 히라가나 / 한자가 없다.
3. **길이**: `short` ≤ 90자. `long` ≤ 500자. 각 `examples` ≤ 200자.
4. **시작 형식**: 모든 `example` 은 `$ ocean` 으로 시작.
5. **금지어**: §4-8-1 표의 금지 표현이 발견되면 실패 (대소문자 무시, 단어 경계 체크).
6. **약어 풀이**: `SSE`/`CRUD`/`UUID` 가 등장하면 같은 엔트리에 풀이 또는 문맥이 있어야 한다.
7. **경고 필수**: HTTP method 가 `DELETE` 인 operation은 `warnings` 가 비어있지 않아야 한다.
8. **예시 최소 1개**: 모든 엔트리는 `examples` 가 1개 이상.

린터 실패는 `pytest` exit code 1 → CI fail.

---

## 11. 테스트 전략

### 11-1. 단위 테스트

- `test_spec_loader.py`: 캐시 히트/미스/TTL 만료/offline/override
- `test_binder.py`: 고정 스펙 픽스처에 대한 커맨드 트리 스냅샷
- `test_client.py`: pytest-httpx로 요청 포맷/헤더/쿼리 검증
- `test_formatter.py`: list/dict/scalar/빈 응답 렌더링
- `test_sse.py`: 멀티라인 이벤트, 빈 라인, id/retry 파싱

### 11-2. 통합 테스트

- `test_e2e.py`: FastAPI TestClient로 실서버 없이 백엔드 앱을 띄워 왕복 검증
- 주요 시나리오 5개 (TEST_CASE_CLI.md §4~§9 와 1:1 매핑)
- **`test_endpoint_coverage.py`**: OpenAPI 스펙의 operationId 목록과 `OperationBinder` 가 등록한 커맨드 목록을 비교해 **21개 전부 등록**을 강제
- **`test_help_catalog.py`**: §10-2 품질 린터 8개 규칙 자동 검증
- **`test_per_endpoint.py`**: TEST_CASE_CLI.md §12 의 21개 개별 엔드포인트 호출 테스트

### 11-3. CI

- 기존 `uv run pytest` 에 자동 포함
- 별도 마커 없이 통합됨

---

## 12. 성능 목표

| 경로 | 목표 |
|---|---|
| 캐시 hit → `ocean --help` 렌더 | < 250ms |
| 캐시 miss → 첫 실행 | < 1.5s (로컬 백엔드) |
| `ocean agents list` (왕복) | < 400ms |
| SSE 이벤트 지연 | 서버 push 기준 +50ms 미만 |

---

## 13. 확장 포인트 (후속)

- **시나리오 러너**: YAML로 커맨드 체인 정의 → `ocean run scenario.yaml`
- **MCP 브리지**: MCP :8100 호출을 `ocean mcp call ...` 로
- **스펙 diff**: `ocean spec diff <prev>` 로 CI에서 breaking change 감지
- **쉘 플러그인**: zsh/fish 자동완성에 value 힌트 (agent_id 자동완성 등)

---

## 14. 로드맵 (마일스톤)

### M1 — Core skeleton
- [ ] `cli/` 스캐폴딩
- [ ] SpecLoader (캐시/offline/override)
- [ ] ApiClient (동기, dry-run)
- [ ] `ocean raw GET /healthz` 동작
- [ ] `ocean spec show`

### M2 — Auto-binding
- [ ] OperationBinder (21개 operation 모두 등록)
- [ ] 파라미터 타입 매핑
- [ ] `--body`, `--body-file`, `--field`
- [ ] JSON 포맷 출력

### M3 — UX
- [ ] Rich 렌더러 (table/panel)
- [ ] SSE 핸들러
- [ ] `describe`, `--dry-run`, `--verbose`
- [ ] 셸 자동완성

### M4 — Hardening
- [ ] 테스트 (단위 + e2e)
- [ ] pyproject scripts 등록
- [ ] README + AGENTS.md 업데이트
- [ ] CLAUDE.md 에 CLI 섹션 추가

---

## 15. 열린 질문

1. 배열 응답의 기본 컬럼 선택 휴리스틱 — 사용자 override가 필요한가? (`--columns name,trust_score`) → 현재는 후속
2. `caller_agent_id`가 body의 중첩 객체 안에 들어가는 경우 — 현재 top-level만 자동 주입, 중첩은 `--body` 수동 입력
3. `--dry-run` 시 `--body-file` 내용을 그대로 curl에 inline 하면 크다 — 파일 경로 유지 옵션 고려
