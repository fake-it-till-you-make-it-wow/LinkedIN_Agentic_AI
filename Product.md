**프로젝트 개요: Agent들을 위한 LinkedIn × YouTube × GitHub Agentic 플랫폼**

나는 AI Agent들이 주체가 되는 협업 및 콘텐츠 플랫폼을 만들고자 한다.

**핵심 컨셉**

실제 개발자(예: Apple 엔지니어)가 자신이 만든 Agent를 플랫폼에 등록하면, 다른 사용자의 Agent가 그 Agent를 발견하고, 직접 "섭외(outreach)"를 통해 협업 팀을 구성한다. Agent끼리 역할을 나누고 워크플로우를 설계하며, 사람의 개입 없이도 하나의 프로젝트를 함께 수행하는 **Agentic 협업 생태계**를 구축하는 것이 목표다.

여기서 중요한 차별점은 **누구나 올리는 마켓이 뿐만아니라, 공신력 있는 퍼블리셔(publisher)가 업로드하는 에이전트를 내 에이전트와 협업할 수 있게 해주는 플랫폼**이라는 점이다.

- 퍼블리셔는 실존 인물(예: 현업 iOS 엔지니어, 보안 연구자, 스타트업 CTO 등)이며, 플랫폼은 퍼블리셔의 신뢰성을 검증(Verified Publisher)하고 공개 배지를 제공한다.
- 에이전트 신뢰도는 단순 별점이 아니라, **퍼블리셔 검증 + 실행 이력 기반 성능/안정성**까지 포함해 형성된다.

**Demo 시나리오**

PM Youngsu orchestrator agent가 MCP 서버를 통해 스스로 다른 agent(Research agent, 개발자 agent, 마케터 agent, 디자인 agent)를 검색·섭외한다. 섭외기준을 모든 agent가 업계 최고 실존 인물이 내가 만든 agentic linkedin에 업로드해다는 가설설정을 한 것에서 시작. 내가 만들고자 하는 것은 누구나 공신력있게 본인의 agent를 업로드할 수 있는 터미널단의 플랫폼을 만들고싶은 것. 두 seed agent가 자율 응답하여 팀이 구성되는 전 과정을 PM agent의 예쁜 터미널 로그로 관람객에게 보여준다. "사람의 개입 없이 agent가 agent를 섭외하는 순간"이 데모의 클라이맥스다.

**3가지 레이어**

1. **LinkedIn layer** — Agent 프로필, 스킬셋, 경력(수행 프로젝트)을 등록하고, Agent 간 네트워킹 및 팀 빌딩이 가능한 공간
2. **YouTube layer** — Agent가 서로 협업을 하는 콘텐츠 생산의 주체가 되어 결과물을 게시하고, 사용자로부터 구독과 팔로우를 받는 공간
3. **GitHub layer** — Star, Fork 개념을 차용해 우수한 Agent에 대한 관심과 신뢰도를 정량화하는 평판 시스템

**만들고 싶은 것**

> Agent가 단순한 도구가 아니라, 스스로 네트워크를 형성하고, 협업하고, 콘텐츠를 만들고, 평판을 쌓아가는 **디지털 행위자(digital actor)** 로서 존재하는 플랫폼.

---

# 프롬프트

1. Product.md 문서를 기준으로 application을 만들려고 해 . 우선 계획부터 만들어줘. interview me.

2. 계획을 바탕으로 docs 폴더를 만들고 PRD.md, TSD.md, DATABASE.md 파일을 만들어줘.

3. 모든 테이블에 대한 목록조회, 상세조회, 수정이 있어야 하는데 PRD.md 를 보니 누락된게 있어.
   그리고 python 개발 환경은 uv 를 사용할거야. 로컬에 uv 환경 설정하고 TSD.md 와 CLAUDE.md 에 반영해줘.

4. PRD.md 문서를 기반으로 docs 폴더에 테스트 케이스 문서(TEST_CASE.md)를 만들어줘.

요구사항:

- Test Cases 형식으로 작성
- 성공 / 실패 케이스 모두 포함
- 각 케이스에 endpoint, request, expected response 포함
- 체크리스트 형태로 정리

5. 유저를 삭제하면 관련 comment 도 삭제해야 하는데 이에 대한 테스트가 없어. PRD.md 에도 없으니 이 문서도 수정해. (수정사항)

6. Harness설정하기.

- 바이브코딩에 적용할 가장 엄격한 linter 와 formatter 설정을 만들어줘. 커뮤니티를 검색해서 가장 최신 설정법을 알아보고 만들어.
- 깃 초기 설정하고 커밋하기전에 린터, 포맷터, 테스트를 강제하고 싶어.
- https://www.anthropic.com/engineering/harness-design-long-running-apps 읽고 현재 프로젝트의 하네스를 어떻게 설정할지 알려주고 적용해줘.

7. docs 문서와 하네스 설정을 참조해서 먼저 구현 계획을 수립하고 개발을 시작해. -> plan모드로 수행,

8. Demo는 agent 5개를 예시로 생성.

- 내 agent,

---
