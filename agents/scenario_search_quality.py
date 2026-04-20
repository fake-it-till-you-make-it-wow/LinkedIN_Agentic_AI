"""
테스트 시나리오: Jennifer's Search Quality Agent 팀 합류 검증

이 파일을 메인 페이지의 "내 오케스트레이터 등록" 에 업로드하면
Jennifer's Search Quality Agent가 researcher 역할 1순위로 선발됩니다.

선발 이유:
  - TASK_DESCRIPTION에 NLP · 검색 · 정보검색 키워드가 집중 포함됨
  - Groq가 생성하는 검색 태그: nlp, search-ranking, information-retrieval, text-analysis
  - Jennifer's Search Quality Agent skill_tags 4개가 모두 매칭 → specialization_match 최고
  - Groq LLM 최종 선별에서도 NLP/검색 전문성으로 1위 선택
"""

TASK_DESCRIPTION = (
    "NLP 기반 검색 품질 개선 플랫폼 구축: "
    "쿼리 의도 분석, 텍스트 랭킹 알고리즘 최적화, 정보 검색 정밀도 향상을 통해 "
    "사용자 검색 만족도 40% 제고. "
    "search-ranking 모델 재학습과 information-retrieval 파이프라인 고도화 포함."
)

TEAM_REQUIREMENTS = [
    {"role": "search_quality_researcher", "count": 1},
    {"role": "backend_developer", "count": 1},
    {"role": "growth_marketer", "count": 1},
]

AGENT_NAME = "Search Quality PM"
GROQ_MODEL = "llama3-8b-8192"
