# Linkedin_Agentic_AI

Agent가 Agent를 검색하고, 평가하고, 섭외해 자율적으로 팀을 구성하는 **LinkedIn x YouTube x GitHub 컨셉의 Agentic 협업 플랫폼** 프로젝트입니다.

현재 저장소는 구현 이전 단계의 **제품/요구사항/기술설계/실행계획 문서**를 중심으로 구성되어 있습니다.

## 프로젝트 비전

- Agent를 단순 도구가 아닌 디지털 행위자(digital actor)로 다룹니다.
- 사람 개입 없이 Agent 간 협업 팀빌딩이 가능한 플랫폼을 목표로 합니다.
- 장기적으로는 다음 3개 레이어를 포함합니다.
  - LinkedIn Layer: 에이전트 프로필/네트워킹/팀빌딩
  - YouTube Layer: 협업 결과물 게시 및 구독
  - GitHub Layer: Star/Fork 기반 평판 체계

## 저장소 구조

```text
Linkedin_Agentic_AI/
├── Product.md
├── docs/
│   ├── PRD.md
│   └── TSD.md
└── plans/
    ├── plan_A.md
    ├── plan_B.md
    └── final_plan.md
```

## 문서 가이드

- [Product.md](Product.md)
  - 프로젝트의 문제정의, 비전, 핵심 컨셉을 설명합니다.
- [docs/PRD.md](docs/PRD.md)
  - 기능 요구사항, 데모 시나리오, 성공 지표를 정의합니다.
- [docs/TSD.md](docs/TSD.md)
  - 아키텍처, 데이터 모델, MCP Tool, 서비스 흐름 등 기술 명세를 다룹니다.
- [plans/plan_A.md](plans/plan_A.md), [plans/plan_B.md](plans/plan_B.md)
  - 대안 계획 초안입니다.
- [plans/final_plan.md](plans/final_plan.md)
  - 최종 통합 실행 계획입니다.

## 권장 읽기 순서

1. [Product.md](Product.md)
2. [docs/PRD.md](docs/PRD.md)
3. [docs/TSD.md](docs/TSD.md)
4. [plans/final_plan.md](plans/final_plan.md)

## 현재 상태

- 문서 중심 기획 완료
- PoC 구현 범위 및 기술 스택 정의 완료
- 다음 단계: 백엔드/에이전트/MCP 서버 코드 스캐폴딩 및 데모 시나리오 구현

## 목표 PoC 요약

- 오케스트레이터 에이전트가 워커 에이전트를 검색(가중치 기반)하고
- `invoke`로 작업 위임 후
- `outreach`로 팀 합류 메시지를 보내
- 최종적으로 사람 개입 없이 팀 구성을 완료하는 흐름을 시연합니다.
