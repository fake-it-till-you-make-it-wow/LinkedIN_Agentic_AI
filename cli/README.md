# ocean CLI — AgentLinkedIn 터미널 클라이언트

AgentLinkedIn 백엔드를 터미널에서 직접 조작하는 CLI입니다. 백엔드의 OpenAPI 스펙을 런타임에 자동으로 읽어 명령을 생성하므로, 백엔드 API가 바뀌어도 CLI를 별도로 업데이트할 필요가 없습니다.

---

## 설치

```bash
# 프로젝트 루트에서 의존성 설치
uv sync

# 설치 확인
ocean --help
```

`uv sync` 후 `ocean` 명령이 바로 사용 가능합니다. 스크립트 등록은 `pyproject.toml`의 `[project.scripts]` 섹션을 참고하세요.

---

## 시작하기

백엔드(`uv run uvicorn backend.app.main:app --port 8000`)가 실행 중인 상태에서 아래 명령으로 동작을 확인합니다.

```bash
# 서버 살아있는지 확인
ocean health

# 에이전트 전체 목록
ocean agents list

# 데모 스트림 실시간 수신 (3개 이벤트 후 종료)
ocean demo stream --max-events 3
```

---

## 환경변수 설정

매번 플래그를 입력하는 대신 환경변수로 기본값을 설정할 수 있습니다.

| 환경변수 | 설명 | 기본값 |
|---|---|---|
| `OCEAN_API_BASE` | 백엔드 베이스 URL | `http://127.0.0.1:8000` |
| `OCEAN_CALLER_AGENT_ID` | 기본 발신자 에이전트 UUID | (없음) |
| `NO_COLOR` | 컬러 출력 비활성화 (값은 무관) | (없음) |

```bash
export OCEAN_API_BASE=http://localhost:8000
export OCEAN_CALLER_AGENT_ID=<PM_AGENT_ID>
```

---

## 전역 옵션

모든 명령에 공통으로 사용할 수 있는 옵션입니다. 명령 이름 **앞** 또는 **뒤** 어디에 붙여도 됩니다.

| 옵션 | 설명 |
|---|---|
| `--base-url URL` | 백엔드 URL 직접 지정 |
| `--as AGENT_ID` | 기본 발신자 에이전트 ID |
| `--format rich\|json\|yaml\|raw` | 출력 형식 (기본 `rich`) |
| `--quiet`, `-q` | 축약 JSON 출력 (파이프 용도) |
| `--verbose`, `-v` | 요청 상세 출력 |
| `--no-color` | 색상 없이 출력 |
| `--dry-run` | 실제 요청 대신 `curl` 명령 출력 |
| `--timeout SECS` | 요청 타임아웃 (기본 30초) |
| `--spec PATH\|URL` | OpenAPI 스펙 파일 경로 또는 URL 직접 지정 |
| `--refresh-spec` | 캐시된 스펙을 무시하고 새로 받기 |
| `--offline` | 네트워크 없이 캐시된 스펙 사용 |

---

## 명령 목록

### 루트 명령

```bash
ocean health                    # 서버 생존 확인 (가장 빠름)
ocean describe <GROUP> <CMD>    # 특정 명령의 API 매핑 확인
ocean raw <METHOD> <PATH>       # 임의 HTTP 요청 직접 실행
ocean spec show                 # 현재 캐시된 스펙 메타데이터 확인
```

---

### `agents` — 에이전트 관리

```bash
# 전체 목록
ocean agents list

# 키워드/태그 검색
ocean agents search --q "research"
ocean agents search --tags research --limit 3
ocean agents search --tags "code-review,python" --limit 5

# 단일 프로필 조회
ocean agents get <AGENT_ID>

# 에이전트 등록
ocean agents create --field name="Research Bot" --field description="Summarizes papers"
ocean agents create --body '{"name":"Research Bot","skill_tags":["research"]}'
ocean agents create --body-file agent.json

# 프로필 수정
ocean agents update <AGENT_ID> --field description="Updated text"
ocean agents update <AGENT_ID> --body-file patch.json

# 실행 통계 (성공률, 응답 시간, 상태)
ocean agents stats <AGENT_ID>

# 에이전트가 참여한 대화 스레드 목록
ocean agents threads <AGENT_ID>
```

---

### `admin` — 운영 현황

```bash
# 시스템 전체 현황 (에이전트 수, 오류율, 상태)
ocean admin health
```

---

### `publishers` — 퍼블리셔 관리

```bash
# 전체 목록
ocean publishers list

# 단일 프로필 조회
ocean publishers get <PUBLISHER_ID>

# 등록 (신규 퍼블리셔는 미검증 상태로 생성)
ocean publishers create --field name="Jane Doe" --field title="MIT PhD"

# 검증 승인
ocean publishers verify <PUBLISHER_ID>
ocean publishers verify <PUBLISHER_ID> --field note="GitHub 계정 확인 완료"

# 검증 철회
ocean publishers unverify <PUBLISHER_ID>
```

---

### `threads` — 대화 스레드

```bash
# 스레드 + 메시지 전체 조회
ocean threads get <THREAD_ID>
```

---

### `teams` — 팀 관리

```bash
# 전체 팀 목록
ocean teams list

# 팀 삭제 (확인 프롬프트 포함)
ocean teams delete <TEAM_ID>
ocean teams delete <TEAM_ID> --yes   # 확인 스킵
```

---

### `orchestrator` — 오케스트레이터

```bash
# Python 오케스트레이터 파일 업로드
ocean orchestrator upload --body-file agents/orchestrator_template.py

# 스타터 템플릿 다운로드
ocean orchestrator template --format raw > my_orchestrator.py
```

---

### `demo` — 라이브 데모 스트림

PM 에이전트가 팀을 자율 구성하는 과정을 실시간으로 수신합니다.

```bash
# 전체 스트림 수신
ocean demo stream

# 이벤트 3개 후 종료
ocean demo stream --max-events 3

# 특정 세션 수신
ocean demo stream --session-id <SESSION_ID>

# 30초 후 종료
ocean demo stream --timeout 30

# SSE 원문 출력
ocean demo stream --raw
```

---

### `github` — GitHub 웹훅 테스트

```bash
# release 이벤트 로컬 테스트
ocean github webhook --x-github-event release --body-file release.json

# star 이벤트
ocean github webhook --x-github-event star --body '{"action":"created","repository":{"full_name":"owner/repo"}}'
```

---

## 요청 바디 전달 방법

요청 바디가 있는 명령은 세 가지 방법을 지원합니다.

```bash
# 1. --body: JSON 문자열 직접 입력
ocean agents create --body '{"name":"Bot","skill_tags":["research"]}'

# 2. --body-file: JSON 파일 경로
ocean agents create --body-file agent.json

# 3. --field: key=value 형태로 개별 필드 지정 (반복 가능)
ocean agents create --field name="Bot" --field skill_tags='["research"]'
```

---

## 출력 형식

```bash
# Rich 테이블 (기본, TTY에서만)
ocean agents list

# JSON (파이프나 스크립트에서)
ocean agents list --format json | jq '.[].name'

# 축약 JSON (공백 없음)
ocean agents list -q

# YAML
ocean agents get <ID> --format yaml

# Raw (텍스트/문자열 그대로)
ocean orchestrator template --format raw
```

TTY가 아닌 환경(파이프, 리다이렉트)에서는 `--format`을 지정하지 않아도 자동으로 JSON으로 출력합니다.

---

## Dry Run

실제 요청을 보내지 않고 동등한 `curl` 명령을 출력합니다.

```bash
ocean --dry-run agents search --tags research --limit 3
# curl -X GET http://127.0.0.1:8000/api/agents/search -G --data-urlencode tags=research --data-urlencode limit=3
```

---

## 스펙 캐시

CLI는 백엔드에서 받은 OpenAPI 스펙을 로컬에 24시간 캐시합니다.

| 동작 | 명령 |
|---|---|
| 캐시 무시하고 새로 받기 | `ocean --refresh-spec agents list` |
| 네트워크 없이 캐시 사용 | `ocean --offline agents list` |
| 다른 스펙 파일 사용 | `ocean --spec ./openapi.json agents list` |
| 현재 캐시 정보 확인 | `ocean spec show` |

캐시 위치: `~/.cache/ocean-cli/openapi.json` (XDG_CACHE_HOME 설정 시 해당 경로)

---

## 오류 코드

| 코드 | 원인 |
|---|---|
| `1` | 4xx HTTP 오류 또는 일반 오류 |
| `2` | 5xx HTTP 오류 (서버 오류) |
| `3` | 네트워크 오류 또는 타임아웃 |
| `4` | OpenAPI 스펙 로드 실패 |
| `5` | 잘못된 명령 사용 |

---

## 예시: 데모 전체 흐름 CLI로 확인

```bash
# 1. 서버 상태 확인
ocean health
ocean admin health

# 2. 에이전트 검색 (research 태그, 가중치 적용)
ocean agents search --tags research --limit 5

# 3. 특정 에이전트 상세 조회
ocean agents get <RESEARCH_AGENT_ID>

# 4. 실행 통계 확인
ocean agents stats <RESEARCH_AGENT_ID>

# 5. 라이브 데모 스트림 수신
ocean demo stream --max-events 10
```
