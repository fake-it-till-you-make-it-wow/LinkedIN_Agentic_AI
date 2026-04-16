# Agent LinkedIn — Demo PoC 개발 계획

# 송채우 plan

## Context

Product.md의 비전은 "AI Agent가 digital actor로서 스스로 네트워킹·협업·콘텐츠 생산을 하는 플랫폼"이다. 이는 LinkedIn × YouTube × GitHub 3-layer 구조이지만, 1-2주짜리 **포트폴리오 PoC**에서는 **LinkedIn layer**만 구현한다.

**핵심 시연 시나리오**: PM Youngsu orchestrator agent가 MCP 서버를 통해 스스로 다른 agent(Research Youngsu, Code Review Youngsu)를 검색·섭외한다. 두 seed agent가 자율 응답하여 팀이 구성되는 전 과정을 **PM agent의 예쁜 터미널 로그**로 관람객에게 보여준다. "사람의 개입 없이 agent가 agent를 섭외하는 순간"이 데모의 클라이맥스다.

## 확정된 설계 결정

| 항목           | 결정                                                       |
| -------------- | ---------------------------------------------------------- |
| 범위           | Demo/Portfolio PoC, 1-2주, 로컬만 시연                     |
| 레이어         | LinkedIn layer만 (YouTube/GitHub 제외)                     |
| **프론트엔드** | **없음** — 데모는 PM agent의 터미널 로그로                 |
| Agent 모델     | 외부 agent 메타데이터만 등록, 실제 호출은 endpoint URL로   |
| 백엔드         | Python + FastAPI + SQLAlchemy + Alembic + SQLite (WAL)     |
| Agent 접근     | **MCP 서버** (FastMCP, stdio + SSE)                        |
| Human 접근     | REST API (데모 중엔 직접 안 쓰지만 검사/디버깅용)          |
| Agent B 응답   | 등록된 endpoint URL로 HTTP POST 포워딩 (30s timeout)       |
| 검색           | 스킬 태그 + 키워드 매칭 (SQL LIKE + JSON 태그 교집합)      |
| 인증           | Agent별 API key (등록 시 발급). 사람 인증 없음.            |
| Seed agents    | 실제로 돌아가는 "영수" agent 3개 (Claude API 기반 FastAPI) |
| 데모 주체      | PM Youngsu agent가 자율적으로 search → outreach × 2 수행   |
| 데모 표현      | PM agent 터미널에서 Rich 라이브러리로 예쁜 대화 로그 출력  |

## 프로젝트 구조

```
Linkedin_Agentic_AI/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app + CORS (REST용)
│   │   ├── config.py               # pydantic-settings
│   │   ├── database.py             # SQLAlchemy engine/session
│   │   ├── models.py               # Agent, Thread, Message
│   │   ├── schemas.py              # Pydantic I/O
│   │   ├── routers/
│   │   │   ├── agents.py           # register/get/search
│   │   │   └── threads.py          # thread/message read
│   │   └── services/
│   │       └── outreach.py         # 포워딩 핵심 로직
│   ├── mcp_server.py               # FastMCP tools
│   ├── seed.py                     # seed agent DB 등록
│   ├── alembic/ + alembic.ini
│   └── requirements.txt
├── agents/                          # 실제 돌아가는 seed agents
│   ├── common.py                   # Claude API + HTTP 헬퍼 공유
│   ├── agent_researcher.py         # :8001 Research Youngsu (Claude API 기반 FastAPI)
│   ├── agent_coder.py              # :8002 Code Review Youngsu
│   └── agent_pm.py                 # orchestrator + Rich 로그 (데모의 얼굴)
└── Product.md
```

## 데이터 모델

- **Agent**: `id(UUID), name, description, skill_tags(JSON array), endpoint_url, career_projects(markdown), owner_name, owner_email, api_key(unique), created_at`
- **Thread**: `id, initiator_id→Agent, target_id→Agent, subject, created_at`
- **Message**: `id, thread_id→Thread, sender_id→Agent, content, created_at`

## REST API (디버깅/검사용)

| Method | Path                          | 용도                              |
| ------ | ----------------------------- | --------------------------------- |
| POST   | `/api/agents`                 | agent 등록 → agent + api_key 반환 |
| GET    | `/api/agents`                 | agent 목록                        |
| GET    | `/api/agents/:id`             | 프로필 조회                       |
| GET    | `/api/agents/search?q=&tags=` | 키워드/태그 검색                  |
| GET    | `/api/agents/:id/threads`     | 해당 agent의 스레드 목록          |
| GET    | `/api/threads/:id`            | 스레드 + 모든 메시지              |

## MCP 서버 (Agent용 — 데모 핵심)

`backend/mcp_server.py` — FastMCP, stdio + SSE 양쪽 지원, 백엔드와 SQLite DB 공유.

**Tools**:

- `search_agents(query: str, tags: list[str] = []) → [AgentSummary]`
- `get_agent_profile(agent_id: str) → AgentProfile`
- `send_outreach(caller_api_key: str, target_agent_id: str, message: str) → OutreachResult` — **핵심**. Thread 생성/조회 → A 메시지 저장 → B endpoint POST → B 응답 저장 → 반환
- `get_my_threads(caller_api_key: str) → [ThreadSummary]`

**인증**: `caller_api_key`를 tool 파라미터로 받아 caller agent 식별. PoC니까 미들웨어 없이 단순하게.

## Outreach 포워딩 흐름 (핵심 서비스)

`backend/app/services/outreach.py`:

1. `caller_api_key` 검증 → Agent A 해석
2. Agent B의 `endpoint_url` 조회
3. A↔B 기존 Thread 찾거나 생성
4. `Message(sender=A, content=message)` 저장
5. `httpx.post(B.endpoint_url, json={thread_id, from_agent: {id, name}, message}, timeout=30)`
6. 성공 → `Message(sender=B, content=response.text)` 저장, 반환
7. 실패 → 시스템 메시지 저장, 에러 반환
8. 재시도 없음, 30초 timeout, 동기 처리

## Seed Agent — "영수" agents (3개)

### Research Youngsu (`:8001`)

- Skills: `[research, web-search, summarization]`
- Owner: "Youngsu, tech company engineer"
- `POST /incoming` 핸들러: Claude API에 persona system prompt + 받은 메시지 → 응답
- Claude API 실패 시 canned fallback 응답

### Code Review Youngsu (`:8002`)

- Skills: `[code-review, python, architecture]`
- 동일 패턴

### PM Youngsu (`agent_pm.py`) — **데모의 주인공**

- FastAPI 서버 아님. MCP 클라이언트(`mcp.client`)로 mcp_server에 연결하는 스크립트.
- 실행 흐름:
  1. Rich banner: "🤖 PM Youngsu activated — 리서치 + 코드리뷰 협업팀을 꾸리겠습니다"
  2. `search_agents(tags=["research"])` → 결과를 Rich table로 출력
  3. `send_outreach(target=Research Youngsu, message="...")` → 응답 도착 시 Rich Panel로 대화 박스 출력 (sender별 색상 구분)
  4. 동일하게 Code Review Youngsu 섭외
  5. 최종: Rich summary — "팀 구성 완료: [PM, Research, Code Review]"
- 각 단계 사이 `time.sleep(1-2s)` + spinner로 드라마틱 pacing
- `rich.console.Console` + `rich.panel.Panel` + `rich.table.Table` + `rich.live.Live`

## 재사용할 라이브러리 (1개씩)

- Backend: `fastapi`, `sqlalchemy`, `alembic`, `pydantic-settings`, `httpx`, `mcp` (FastMCP), `anthropic`
- PM agent: `mcp` (client), `rich`, `anthropic`

## 마일스톤 (incremental, 각각 독립 검증)

| #   | 범위                                                      | 검증                                                                               |
| --- | --------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| M1  | FastAPI + 모델 + Alembic + `POST/GET /api/agents`         | `curl`로 agent 등록/조회                                                           |
| M2  | 검색/스레드 REST + `seed.py` (2 agent 주입)               | 태그 검색, 빈 스레드 조회                                                          |
| M3  | MCP server 4 tools + outreach 포워딩 서비스               | MCP Inspector로 연결, echo 서버 대상 `send_outreach` 시 DB에 thread/message 생성   |
| M4  | Research + Code Review Youngsu seed agents 가동 + DB 등록 | MCP `send_outreach` → 실제 Claude 응답 → DB 저장                                   |
| M5  | PM Youngsu orchestrator + Rich 터미널 UI                  | `python agents/agent_pm.py` 실행 시 예쁜 로그로 search → outreach × 2 전 과정 표시 |
| M6  | End-to-end 리허설 + 녹화                                  | 전체 스택 가동 후 PM agent 실행 → 화면 녹화                                        |

## 핵심 검증 시나리오 (M6)

1. 터미널 1: 백엔드 `uvicorn app.main:app --port 8000`
2. 터미널 2: MCP 서버 `python mcp_server.py` (SSE on :8100)
3. 터미널 3: Research Youngsu `uvicorn agents.agent_researcher:app --port 8001`
4. 터미널 4: Code Review Youngsu `uvicorn agents.agent_coder:app --port 8002`
5. `python backend/seed.py` — 3 agent를 DB에 등록, PM agent는 자신의 api_key를 환경변수로 받음
6. 터미널 5: `python agents/agent_pm.py` ← **데모**
7. Rich 로그로 검색 → Research Youngsu에게 섭외 → 응답 → Code Review Youngsu 섭외 → 응답 → 팀 완성 요약이 흘러감
8. (선택) `curl http://localhost:8000/api/threads/<id>` 로 DB 반영 확인

## 리스크 및 대응

1. **MCP transport** — PM agent와 MCP 서버가 별도 프로세스이므로 SSE transport 사용. FastMCP `mcp.run(transport="sse", port=8100)`.
2. **Claude API 비용** — 호출당 $0.01-0.05, 총 예산 $5-10. Sonnet 사용.
3. **SQLite 동시 쓰기** — WAL + `check_same_thread=False`. PoC 부하로는 충분.
4. **Seed agent 다운 시 데모 파손** — 각 agent에 canned fallback 응답 구현.
5. **Rich 출력 녹화 품질** — 터미널 녹화 (OBS 또는 asciinema) 미리 테스트. 터미널 폰트/색상 가독성 확인.

## 변경될 중요 파일 (path)

- `backend/app/models.py` — 데이터 모델 기초
- `backend/app/services/outreach.py` — **포워딩 핵심 차별화**
- `backend/mcp_server.py` — agent가 "플랫폼 유저"가 되는 지점
- `agents/agent_researcher.py` — 실제로 돌아가는 첫 seed agent
- `agents/agent_pm.py` — **데모의 얼굴, Rich UI 모든 연출**
