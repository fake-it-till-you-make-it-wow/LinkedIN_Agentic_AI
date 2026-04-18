"""API integration tests."""

from __future__ import annotations

from backend.app.models import Agent


def test_create_get_and_patch_agent(app_client) -> None:
    payload = {
        "name": "Minimal Agent",
        "skill_tags": ["research"],
        "publisher_name": "Tester",
    }
    create_response = app_client.post("/api/agents", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Minimal Agent"
    assert created["trust_score"] == 0.46

    get_response = app_client.get(f"/api/agents/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["publisher_name"] == "Tester"

    patch_response = app_client.patch(
        f"/api/agents/{created['id']}",
        json={"publisher_verified": True, "verified": True, "star_rating": 4.5},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["publisher_verified"] is True
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
        publisher_verified=True,
    )
    minimum = Agent(
        name="Min",
        skill_tags=[],
        star_rating=0.0,
        success_rate=0.0,
        avg_response_ms=6000,
        verified=False,
        publisher_verified=False,
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
