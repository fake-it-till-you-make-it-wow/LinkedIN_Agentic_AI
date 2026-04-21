---
name: team-builder
description: 프로젝트 시나리오를 자연어로 설명하면 오케스트레이터 템플릿을 채우고 AgentLinkedIn CLI로 팀을 자동 결성합니다. 사용자가 "팀 만들어줘", "팀 빌더", "/team-builder", 또는 프로젝트 시나리오와 함께 팀 구성을 요청할 때 트리거.
allowed-tools: Write, Bash, Read
---

사용자의 프로젝트 시나리오를 분석해 AgentLinkedIn 팀 결성 데모를 자동 실행한다.

## 가용 역할

AgentLinkedIn에 등록된 에이전트 역할은 아래 4개뿐이다. TEAM_REQUIREMENTS는 이 중에서만 선택한다.

| role | 전문 영역 |
|---|---|
| `"researcher"` | 시장 분석, 경쟁사 조사, 트렌드 리포트 |
| `"coder"` | 코드 리뷰, 아키텍처 설계, 리팩토링 |
| `"marketer"` | SNS 전략, 콘텐츠 마케팅, 그로스 해킹 |
| `"designer"` | UI/UX 디자인, 프로토타이핑, 디자인 시스템 |

## 실행 순서

### 1단계 — 시나리오 분석

사용자 입력을 읽고 아래 4개 값을 결정한다.

- **TASK_DESCRIPTION**: 미션을 한 문장으로 요약. 구체적이고 행동 지향적으로.
- **TEAM_REQUIREMENTS**: 시나리오에 맞는 역할 선택 (최소 1개, 최대 4개). count는 1~2. 명시되지 않아도 합리적으로 추론.
- **AGENT_NAME**: 프로젝트 성격을 반영한 PM 이름 (예: `"HealthTech PM Agent"`).
- **GROQ_MODEL**: `"llama3-8b-8192"` 고정.

시나리오가 너무 짧거나 역할을 특정할 수 없으면 먼저 1~2개 질문으로 보완한 뒤 진행한다.

### 2단계 — 템플릿 파일 작성

Read 도구로 `agents/orchestrator_template.py`를 읽은 후, Write 도구로 아래 형식으로 덮어쓴다.

```python
# AgentLinkedIn — 오케스트레이터 템플릿
#
# 이 파일을 수정해서 AgentLinkedIn에 업로드하면, 당신의 오케스트레이터 에이전트가
# 아래에 정의된 미션과 팀 구성 요건으로 팀을 자율적으로 섭외합니다.
#
# 필수 항목:
#   TASK_DESCRIPTION  - 오케스트레이터가 달성할 미션 (문자열)
#   TEAM_REQUIREMENTS - 섭외할 역할 목록 (리스트)
#
# 선택 항목:
#   AGENT_NAME  - 이 오케스트레이터의 이름 (기본값: "My Orchestrator")
#   GROQ_MODEL  - Groq 모델 이름 (기본값: "llama3-8b-8192")

TASK_DESCRIPTION = "<결정된 미션>"

TEAM_REQUIREMENTS = [
    {"role": "<역할>", "count": <숫자>},
]

AGENT_NAME = "<결정된 이름>"

GROQ_MODEL = "llama3-8b-8192"
```

### 3단계 — 업로드

```bash
cd C:/Users/chewo/CoCone_session/Linkedin_Agentic_AI && ocean --format json orchestrator upload --body-file agents/orchestrator_template.py
```

응답 JSON에서 `session_id` 추출. 실패 시 원인을 설명하고 중단.

오류가 발생하면 백엔드 기동 여부를 확인하도록 안내한다:
```
uv run uvicorn backend.app.main:app --port 8000
```

### 4단계 — 데모 스트림

```bash
cd C:/Users/chewo/CoCone_session/Linkedin_Agentic_AI && ocean demo stream --session-id <session_id>
```

SSE 이벤트 스트림이 종료될 때까지 대기한다. 백엔드가 자동 종료한다.

### 5단계 — 결과 요약

데모 완료 후 출력:
- 설정된 미션 (TASK_DESCRIPTION)
- 구성된 팀 역할 목록
- session_id

---

`GROQ_API_KEY`가 없어도 canned fallback으로 데모가 정상 동작한다.
