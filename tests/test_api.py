"""API integration tests."""

from __future__ import annotations

import json

from backend.app.models import Agent, InvokeLog, Publisher, Review


def test_create_get_and_patch_agent(app_client, db_session) -> None:
    publisher = Publisher(name="Tester")
    db_session.add(publisher)
    db_session.commit()

    payload = {
        "name": "Minimal Agent",
        "skill_tags": ["research"],
        "publisher_id": publisher.id,
    }
    create_response = app_client.post("/api/agents", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Minimal Agent"
    assert created["publisher"]["name"] == "Tester"
    assert created["publisher"]["verified"] is False
    assert created["trust_score"] == 0.46

    get_response = app_client.get(f"/api/agents/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["publisher"]["name"] == "Tester"

    verify_response = app_client.post(f"/api/publishers/{publisher.id}/verify")
    assert verify_response.status_code == 200
    assert verify_response.json()["verified"] is True

    patch_response = app_client.patch(
        f"/api/agents/{created['id']}",
        json={"verified": True, "star_rating": 4.5},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["publisher"]["verified"] is True
    assert patch_response.json()["trust_score"] > created["trust_score"]


def test_search_agents_returns_weighted_results(app_client, db_session) -> None:
    db_session.add_all(
        [
            Agent(
                name="Researcher",
                skill_tags=["research", "market-analysis"],
                star_rating=4.8,
                success_rate=0.95,
                avg_response_ms=900,
            ),
            Agent(
                name="Designer",
                skill_tags=["ui-design"],
                star_rating=4.9,
                success_rate=0.92,
                avg_response_ms=1100,
            ),
        ]
    )
    db_session.commit()

    response = app_client.get(
        "/api/agents/search", params={"tags": "research", "limit": 5}
    )
    assert response.status_code == 200
    results = response.json()
    assert results[0]["name"] == "Researcher"
    assert results[0]["specialization_match"] == 1.0


def test_trust_score_boundaries() -> None:
    maximum = Agent(
        name="Max",
        skill_tags=[],
        star_rating=5.0,
        success_rate=1.0,
        avg_response_ms=0,
        verified=True,
        publisher=Publisher(name="Max Publisher", verified=True),
    )
    minimum = Agent(
        name="Min",
        skill_tags=[],
        star_rating=0.0,
        success_rate=0.0,
        avg_response_ms=6000,
        verified=False,
    )

    assert maximum.trust_score == 1.0
    assert minimum.trust_score == 0.0


def test_thread_detail_endpoint(app_client, db_session, monkeypatch) -> None:
    from backend.app.models import Message, Thread
    from backend.app.services.outreach import send_outreach

    async def fake_post_json(
        url: str, payload: dict, timeout: float = 30.0
    ) -> dict[str, str]:
        del url, payload, timeout
        return {"response": "함께하겠습니다."}

    monkeypatch.setattr("backend.app.services.outreach.post_json", fake_post_json)

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(name="Target", skill_tags=["research"], endpoint_url="http://worker")
    db_session.add_all([caller, target])
    db_session.commit()

    result = __import__("asyncio").run(
        send_outreach(db_session, caller.id, target.id, "합류 요청")
    )
    thread_id = result.thread_id

    response = app_client.get(f"/api/threads/{thread_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == thread_id
    assert len(body["messages"]) == 2

    assert db_session.query(Thread).count() == 1
    assert db_session.query(Message).count() == 2


def test_create_agent_missing_name_returns_422(app_client) -> None:
    """TC-01-02: 필수 필드 누락 시 422."""

    response = app_client.post(
        "/api/agents", json={"description": "이름 없는 에이전트"}
    )
    assert response.status_code == 422
    body = response.json()
    fields = {tuple(err.get("loc", [])) for err in body.get("detail", [])}
    assert ("body", "name") in fields


def test_search_multi_tag_prioritizes_full_match(app_client, db_session) -> None:
    """TC-03-03: 다중 태그 교집합이 큰 에이전트가 상위."""

    db_session.add_all(
        [
            Agent(
                name="CodeAgent",
                skill_tags=["python", "code-review", "architecture"],
                star_rating=4.7,
                success_rate=0.9,
                avg_response_ms=900,
            ),
            Agent(
                name="Researcher",
                skill_tags=["research", "market-analysis"],
                star_rating=4.8,
                success_rate=0.95,
                avg_response_ms=900,
            ),
        ]
    )
    db_session.commit()

    response = app_client.get(
        "/api/agents/search", params={"tags": "python,code-review", "limit": 5}
    )
    assert response.status_code == 200
    results = response.json()
    assert results[0]["name"] == "CodeAgent"
    assert results[0]["specialization_match"] == 1.0
    other = next(item for item in results if item["name"] == "Researcher")
    assert other["specialization_match"] == 0.0


def test_search_custom_weights_amplifies_specialization(app_client, db_session) -> None:
    """TC-03-02: specialization 가중치 상향 시 점수 차이가 벌어진다."""

    db_session.add_all(
        [
            Agent(
                name="Researcher",
                skill_tags=["research"],
                star_rating=4.0,
                success_rate=0.9,
                avg_response_ms=1000,
            ),
            Agent(
                name="Generalist",
                skill_tags=["general"],
                star_rating=4.9,
                success_rate=0.99,
                avg_response_ms=500,
            ),
        ]
    )
    db_session.commit()

    default = app_client.get(
        "/api/agents/search", params={"tags": "research", "limit": 5}
    ).json()
    default_gap = next(
        item["final_score"] for item in default if item["name"] == "Researcher"
    ) - next(item["final_score"] for item in default if item["name"] == "Generalist")

    custom = app_client.get(
        "/api/agents/search",
        params={
            "tags": "research",
            "weights": json.dumps(
                {
                    "star_rating": 0.1,
                    "specialization": 0.7,
                    "response_speed": 0.1,
                    "success_rate": 0.1,
                }
            ),
            "limit": 5,
        },
    ).json()
    custom_gap = next(
        item["final_score"] for item in custom if item["name"] == "Researcher"
    ) - next(item["final_score"] for item in custom if item["name"] == "Generalist")

    assert custom[0]["name"] == "Researcher"
    assert custom_gap > default_gap


def test_publisher_verification_workflow(app_client) -> None:
    """Phase 2-B: publisher 등록 → 미검증 상태 → verify → unverify."""

    create_response = app_client.post(
        "/api/publishers",
        json={"name": "Workflow Publisher", "title": "Tester"},
    )
    assert create_response.status_code == 201
    publisher = create_response.json()
    assert publisher["verified"] is False
    assert publisher["verified_at"] is None

    duplicate = app_client.post(
        "/api/publishers",
        json={"name": "Workflow Publisher"},
    )
    assert duplicate.status_code == 409

    verify_response = app_client.post(
        f"/api/publishers/{publisher['id']}/verify",
        json={"note": "링크드인 프로필 확인"},
    )
    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["verified"] is True
    assert body["verified_at"] is not None
    assert body["verification_note"] == "링크드인 프로필 확인"

    unverify_response = app_client.post(f"/api/publishers/{publisher['id']}/unverify")
    assert unverify_response.status_code == 200
    assert unverify_response.json()["verified"] is False
    assert unverify_response.json()["verified_at"] is None


def test_publisher_verification_affects_trust_score(app_client, db_session) -> None:
    """publisher.verified 변경이 에이전트 trust_score에 즉시 반영된다."""

    publisher = Publisher(name="Trust Source")
    db_session.add(publisher)
    db_session.commit()

    agent_response = app_client.post(
        "/api/agents",
        json={
            "name": "Trust Agent",
            "skill_tags": ["research"],
            "publisher_id": publisher.id,
            "star_rating": 4.0,
            "success_rate": 0.9,
            "avg_response_ms": 1000,
            "verified": True,
        },
    )
    before = agent_response.json()["trust_score"]

    app_client.post(f"/api/publishers/{publisher.id}/verify")
    after_response = app_client.get(f"/api/agents/{agent_response.json()['id']}")
    after = after_response.json()["trust_score"]

    assert after == round(before + 0.05, 4)


def test_agent_stats_aggregates_invokes_and_reviews(app_client, db_session) -> None:
    """Phase 2.1: /api/agents/{id}/stats가 InvokeLog + Review 집계를 반환."""

    caller = Agent(name="Caller", skill_tags=["pm"])
    target = Agent(
        name="Target", skill_tags=["research"], endpoint_url="http://x", star_rating=4.0
    )
    db_session.add_all([caller, target])
    db_session.flush()
    db_session.add_all(
        [
            InvokeLog(
                caller_id=caller.id,
                target_id=target.id,
                input_data=None,
                status="success",
                response_ms=900,
            ),
            InvokeLog(
                caller_id=caller.id,
                target_id=target.id,
                input_data=None,
                status="success",
                response_ms=1100,
            ),
            InvokeLog(
                caller_id=caller.id,
                target_id=target.id,
                input_data=None,
                status="error",
                response_ms=200,
            ),
            Review(caller_id=caller.id, target_id=target.id, rating=4.5),
        ]
    )
    db_session.commit()

    response = app_client.get(f"/api/agents/{target.id}/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_invocations"] == 3
    assert body["success_count"] == 2
    assert body["error_count"] == 1
    assert body["timeout_count"] == 0
    assert body["success_rate"] == round(2 / 3, 4)
    assert body["avg_response_ms"] == 1000
    assert body["review_count"] == 1
    assert body["status"] in {"degraded", "failing"}


def test_agent_stats_idle_when_no_history(app_client, db_session) -> None:
    agent = Agent(name="Fresh", skill_tags=["new"])
    db_session.add(agent)
    db_session.commit()

    response = app_client.get(f"/api/agents/{agent.id}/stats")
    body = response.json()
    assert body["total_invocations"] == 0
    assert body["status"] == "idle"
    assert body["avg_response_ms"] is None
    assert body["last_invoked_at"] is None


def test_admin_health_reports_counts_and_status(app_client, db_session) -> None:
    """Phase 2.1: /api/admin/health가 시스템 전체 카운터와 상태 플래그 반환."""

    pub = Publisher(name="Ops Pub", verified=True)
    agent = Agent(name="Ops Agent", skill_tags=["ops"], verified=True, publisher=pub)
    other = Agent(name="Other", skill_tags=["misc"])
    db_session.add_all([pub, agent, other])
    db_session.flush()
    db_session.add_all(
        [
            InvokeLog(
                caller_id=other.id,
                target_id=agent.id,
                input_data=None,
                status="success",
                response_ms=500,
            ),
            InvokeLog(
                caller_id=other.id,
                target_id=agent.id,
                input_data=None,
                status="success",
                response_ms=600,
            ),
            Review(caller_id=other.id, target_id=agent.id, rating=5.0),
        ]
    )
    db_session.commit()

    response = app_client.get("/api/admin/health")
    assert response.status_code == 200
    body = response.json()
    assert body["agents_total"] == 2
    assert body["agents_verified"] == 1
    assert body["publishers_total"] == 1
    assert body["publishers_verified"] == 1
    assert body["invocations_total"] == 2
    assert body["invocation_error_rate"] == 0.0
    assert body["reviews_total"] == 1
    assert body["status"] == "healthy"


def test_search_without_query_returns_zero_semantic(app_client, db_session) -> None:
    """Phase 3-A: q가 없으면 semantic_score는 모두 0."""

    db_session.add(Agent(name="Solo", skill_tags=["research"], description="anything"))
    db_session.commit()

    response = app_client.get(
        "/api/agents/search", params={"tags": "research", "limit": 5}
    )
    assert response.status_code == 200
    results = response.json()
    assert results[0]["semantic_score"] == 0.0


def test_search_semantic_score_positive_when_query_matches(
    app_client, db_session
) -> None:
    """Phase 3-A: q에 매칭되는 토큰이 있으면 semantic_score > 0."""

    db_session.add(
        Agent(
            name="ML Researcher",
            description="machine learning research specialist",
            skill_tags=["research"],
            star_rating=4.0,
            success_rate=0.9,
            avg_response_ms=1000,
        )
    )
    db_session.commit()

    response = app_client.get(
        "/api/agents/search",
        params={"q": "machine learning", "limit": 5},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["semantic_score"] > 0.0
    assert results[0]["final_score"] > 0.0


def test_github_webhook_release_records_version(app_client, db_session) -> None:
    """Phase 3-B: release 이벤트가 AgentRelease 행을 생성한다."""

    from backend.app.models import AgentRelease

    agent = Agent(name="Repo Agent", skill_tags=["ml"], github_repo="acme/agent")
    db_session.add(agent)
    db_session.commit()

    response = app_client.post(
        "/api/github/webhook",
        headers={"X-GitHub-Event": "release"},
        json={
            "action": "published",
            "repository": {"full_name": "acme/agent"},
            "release": {
                "tag_name": "v1.0.0",
                "name": "First release",
                "body": "notes",
                "published_at": "2026-04-19T10:00:00Z",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["tag"] == "v1.0.0"

    releases = db_session.query(AgentRelease).all()
    assert len(releases) == 1
    assert releases[0].tag == "v1.0.0"
    assert releases[0].name == "First release"


def test_github_webhook_star_updates_count(app_client, db_session) -> None:
    """Phase 3-B: star 이벤트가 stargazers_count로 동기화된다."""

    agent = Agent(
        name="Star Agent",
        skill_tags=["ml"],
        github_repo="acme/star",
        github_star_count=0,
    )
    db_session.add(agent)
    db_session.commit()

    response = app_client.post(
        "/api/github/webhook",
        headers={"X-GitHub-Event": "star"},
        json={
            "action": "created",
            "repository": {"full_name": "acme/star", "stargazers_count": 42},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["star_count"] == 42

    db_session.expire_all()
    assert db_session.get(Agent, agent.id).github_star_count == 42


def test_github_webhook_ignores_unknown_repo(app_client, db_session) -> None:
    """Phase 3-B: 매칭되는 Agent가 없으면 ignored."""

    del db_session
    response = app_client.post(
        "/api/github/webhook",
        headers={"X-GitHub-Event": "release"},
        json={
            "action": "published",
            "repository": {"full_name": "someone/unknown"},
            "release": {"tag_name": "v0.1.0"},
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_agent_community_score_saturates(db_session) -> None:
    """Phase 3-B: community_score는 star=0에서 0, star=100에서 1.0으로 수렴."""

    zero = Agent(name="Fresh", skill_tags=[], github_star_count=0)
    mid = Agent(name="Mid", skill_tags=[], github_star_count=10)
    cap = Agent(name="Cap", skill_tags=[], github_star_count=100)
    over = Agent(name="Over", skill_tags=[], github_star_count=1000)
    db_session.add_all([zero, mid, cap, over])
    db_session.commit()

    assert zero.community_score == 0.0
    assert 0 < mid.community_score < 1.0
    assert cap.community_score == 1.0
    assert over.community_score == 1.0


def test_search_limit_caps_results(app_client, db_session) -> None:
    """TC-03-06: limit 파라미터가 반환 개수를 제한한다."""

    db_session.add_all(
        [Agent(name=f"Agent{i}", skill_tags=["research"]) for i in range(3)]
    )
    db_session.commit()

    response = app_client.get(
        "/api/agents/search", params={"tags": "research", "limit": 1}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
