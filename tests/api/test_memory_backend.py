from fastapi.testclient import TestClient


def test_memory_backend_plays_a_session_without_mongo(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    created = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]
    choice = created.json()["view"]["eligible_actions"][0]["action_id"]

    stepped = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": choice})
    assert stepped.status_code == 200, stepped.text
    assert client.get(f"/v1/sessions/{session_id}").status_code == 200


def test_real_app_defaults_to_developer_projection(monkeypatch) -> None:
    # The web client opts into the player projection; everything else gets developer detail.
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import create_app

    body = TestClient(create_app()).get("/v1/sessions/nonexistent").json()
    for member in ("detail", "effect", "recovery", "signal"):
        assert member in body, body
