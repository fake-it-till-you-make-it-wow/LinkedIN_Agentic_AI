# CLAUDE.md — AgentLinkedIn 프로젝트 지침

## 프로젝트 개요

AI 에이전트가 다른 에이전트를 자율적으로 검색/평가/섭외하여 팀을 구성하는 플랫폼.
공신력 있는 퍼블리셔(실존 업계 전문가)가 에이전트를 등록하고, 에이전트 간 자율 협업이 이루어진다.

## 기술 스택

- Python 3.12+, uv (monorepo)
- FastAPI + SQLAlchemy 2.0 + Alembic + SQLite (WAL)
- FastMCP (SSE transport :8100)
- Rich 13+ (터미널 UI)
- LLM: Groq/Anthropic/Gemini (환경변수 스위칭)

## 핵심 규칙

- **인증 없음**: api_key 사용하지 않는다. Agent 식별은 UUID(agent_id)로만 수행.
- **agents/common.py 수정 금지**: 기존 LLM 백엔드 추상화 코드를 그대로 사용한다.
- **MCP Tool 파라미터**: `caller_api_key`가 아닌 `caller_agent_id` 사용.
- **환경변수**: `PM_API_KEY`가 아닌 `PM_AGENT_ID` 사용.

## 코딩 컨벤션

- 타입 힌트 필수 (mypy strict 모드)
- docstring은 Google 스타일, 한국어 허용
- import 정렬은 ruff isort 자동 처리
- 모든 LLM 호출에 try/except + canned fallback 필수
- UUID는 String(36)으로 SQLite 저장

## 하네스 설계 (Anthropic Harness Pattern)

> 참고: https://www.anthropic.com/engineering/harness-design-long-running-apps

이 프로젝트는 3-에이전트 하네스 패턴을 적용한다:

### 1. Planner (Claude)
- 아키텍처 설계, 마일스톤 분해, 기술 명세 작성
- 파일 기반 소통: `docs/PRD.md`, `docs/TSD.md`, 울트라플랜
- "무엇을 만들 것인가"에 집중

### 2. Generator (Codex)
- 마일스톤 순차로 코드 생성 (M0 → M1 → ... → M6)
- `AGENTS.md` 읽고 코딩 컨벤션 준수
- 각 마일스톤 완료 후 `uv run ruff check .` + `uv run pytest` 통과 필수

### 3. Evaluator (Claude)
- Generator가 작성한 코드를 리뷰
- TEST_CASE.md 기준으로 기능 검증
- 발견된 버그는 구체적 재현 방법과 함께 보고

### 하네스 원칙
- **관심사 분리**: 만드는 사람(Generator)과 판단하는 사람(Evaluator)을 분리
- **파일 기반 핸드오프**: 대화가 아닌 문서(PRD/TSD/AGENTS.md)로 컨텍스트 전달
- **측정 가능한 기준**: TEST_CASE.md의 39개 테스트 케이스가 성공 기준
- **반복 피드백 루프**: Generator → Evaluator → 수정 → 재평가
- **점진적 단순화**: 모델 능력 향상 시 하네스 제약을 줄여나간다

## 실행 명령어

```bash
# 의존성 설치
uv sync

# 린터/포맷터
uv run ruff check .            # lint
uv run ruff check --fix .      # lint + auto-fix
uv run ruff format .           # format

# 타입 체크
uv run mypy backend/ agents/

# 테스트
uv run pytest

# pre-commit 설치
uvx pre-commit install

# pre-commit 수동 실행
uvx pre-commit run --all-files

# DB 마이그레이션
uv run alembic -c backend/alembic.ini upgrade head

# 서버 실행
uv run uvicorn backend.app.main:app --port 8000
uv run python backend/mcp_server.py
uv run uvicorn agents.agent_researcher:app --port 8001
uv run uvicorn agents.agent_coder:app --port 8002
uv run uvicorn agents.agent_marketer:app --port 8003
uv run uvicorn agents.agent_designer:app --port 8004
```

## 디렉토리 구조

```
Linkedin_Agentic_AI/
├── pyproject.toml            uv monorepo
├── CLAUDE.md                 이 파일
├── AGENTS.md                 Codex용 공유 지침
├── backend/                  FastAPI + MCP 서버
│   ├── app/                  메인 앱
│   │   ├── models.py         Agent, Thread, Message, InvokeLog
│   │   ├── services/         scoring, outreach, invoke
│   │   └── routers/          REST API
│   ├── mcp_server.py         MCP 6 tools (SSE :8100)
│   └── seed.py               5개 seed agent 등록
├── agents/                   seed agents
│   ├── common.py             LLM 추상화 (수정 금지)
│   ├── agent_researcher.py   :8001
│   ├── agent_coder.py        :8002
│   ├── agent_marketer.py     :8003
│   ├── agent_designer.py     :8004
│   └── agent_pm.py           오케스트레이터 (MCP 클라이언트)
└── docs/                     PRD, TSD, TEST_CASE
```
