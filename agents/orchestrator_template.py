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

TASK_DESCRIPTION = "6주 안에 SaaS MVP 론칭하기"

TEAM_REQUIREMENTS = [
    {"role": "researcher", "count": 1},
    {"role": "coder", "count": 2},
    {"role": "marketer", "count": 1},
]

AGENT_NAME = "My PM Agent"

GROQ_MODEL = "llama3-8b-8192"
