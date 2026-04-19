"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파일 역할] FastAPI 애플리케이션 진입점 (Entry Point)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【무엇을 하는 파일인가?】
  이 파일은 백엔드 서버의 "시작점"입니다.
  FastAPI 앱을 만들고, 모든 라우터(URL 묶음)를 등록하며,
  서버 시작·종료 시 실행할 초기화 로직을 정의합니다.

【서버 실행 명령어】
  uv run uvicorn backend.app.main:app --port 8000

【등록된 라우터(URL 그룹)】
  ┌────────────────────────┬──────────────────────────────────────────┐
  │ 라우터 파일            │ 담당 URL 경로                            │
  ├────────────────────────┼──────────────────────────────────────────┤
  │ routers/admin.py       │ /api/admin/...  (시스템 관리용 API)      │
  │ routers/agents.py      │ /api/agents/... (에이전트 CRUD API)      │
  │ routers/github.py      │ /api/github/... (GitHub 웹훅 수신)       │
  │ routers/publishers.py  │ /api/publishers/... (퍼블리셔 관리 API) │
  │ routers/threads.py     │ /api/threads/... (대화 스레드 API)      │
  └────────────────────────┴──────────────────────────────────────────┘

【API 문서 자동 생성】
  서버 실행 후 http://localhost:8000/docs 에서 Swagger UI로 모든 API를 확인할 수 있습니다.

【관련 파일】
  - backend/app/config.py    : 환경변수/설정값 관리
  - backend/app/database.py  : DB 연결·초기화
  - backend/app/models.py    : ORM 테이블 정의
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.database import configure_database, healthcheck_query, init_database
from backend.app.routers.admin import router as admin_router
from backend.app.routers.agents import router as agents_router
from backend.app.routers.demo import router as demo_router
from backend.app.routers.github import router as github_router
from backend.app.routers.publishers import router as publishers_router
from backend.app.routers.threads import router as threads_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """서버 시작(startup)과 종료(shutdown) 시 실행되는 수명 주기 관리자.

    【동작 순서】
      서버 시작 시:
        1. configure_database() — SQLite 연결 URL, WAL 모드 등 DB 설정 적용
        2. init_database()      — 테이블이 없으면 생성 (최초 실행 시 자동 스키마 생성)
        3. healthcheck_query()  — SELECT 1 로 DB 정상 동작 확인
        4. yield                — 서버가 요청을 처리하기 시작
      서버 종료 시:
        yield 이후 블록이 실행 (현재는 별도 정리 로직 없음)

    【@asynccontextmanager란?】
      Python의 비동기 컨텍스트 매니저 데코레이터입니다.
      yield 이전 = 서버 시작 시 실행, yield 이후 = 서버 종료 시 실행.
    """
    configure_database()  # DB URL, 연결 옵션 설정
    init_database()  # 테이블 자동 생성
    healthcheck_query()  # DB 연결 상태 확인
    yield  # ← 이 지점부터 서버가 HTTP 요청을 받기 시작


def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스를 생성하고 설정한다.

    【팩토리 패턴 사용 이유】
      app = FastAPI(...) 를 직접 쓰지 않고 함수로 감싸면
      테스트 시 설정을 바꿔서 앱을 새로 만들기 쉽습니다.

    Returns:
        설정이 완료된 FastAPI 앱 인스턴스
    """
    settings = get_settings()

    # FastAPI 앱 생성 (앱 이름은 settings에서 읽음, 수명 주기 관리자 연결)
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # ── CORS 미들웨어 ─────────────────────────────────────────────────────
    # Phase 3-E에서 브라우저 EventSource로 /api/demo/stream에 접근하기 위해
    # 활성화. MVP는 전체 허용, Phase 4에서 origin 화이트리스트로 제한 예정.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 라우터 등록 (각 라우터의 URL prefix는 해당 파일에서 정의됨) ──────
    app.include_router(admin_router)  # 관리자 API
    app.include_router(agents_router)  # 에이전트 CRUD
    app.include_router(demo_router)  # Phase 3-E 라이브 데모 SSE
    app.include_router(github_router)  # GitHub 웹훅
    app.include_router(publishers_router)  # 퍼블리셔 관리
    app.include_router(threads_router)  # 대화 스레드

    # ── 헬스체크 엔드포인트 ────────────────────────────────────────────────
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """서버가 살아있는지 확인하는 헬스체크 엔드포인트.

        로드 밸런서나 모니터링 도구가 주기적으로 호출합니다.
        DB 장애와 무관하게 서버 프로세스 자체가 응답하는지만 확인합니다.
        """
        return {"status": "ok"}

    return app


# ── 앱 인스턴스 생성 (uvicorn이 이 객체를 참조함) ──────────────────────────
# `uvicorn backend.app.main:app` 에서 "app" 이 바로 이 객체입니다.
app = create_app()
