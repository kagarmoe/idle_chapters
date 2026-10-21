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


def test_broken_content_fails_health_and_is_never_cached(monkeypatch) -> None:
    from idle_chapters.api import deps
    from idle_chapters.content import repo as content_repo
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)
    monkeypatch.setattr(deps, "_CONTENT_REPO", None)

    broken = content_repo.ContentRepo()
    broken.npcs_by_id["ghost"] = {"npc_id": "ghost", "home_location_id": "nowhere_place"}
    monkeypatch.setattr(content_repo, "ContentRepo", lambda: broken)

    from idle_chapters.api.server import create_app

    res = TestClient(create_app()).get("/health")
    assert res.status_code == 500, res.text
    assert res.json()["type"].endswith("engine_failure")
    assert "nowhere_place" in res.json()["detail"]
    assert deps._CONTENT_REPO is None


def test_travel_walks_every_path_and_gives_the_kit_once(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    created = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = created.json()["session_id"]
    offered = {a["action_id"] for a in created.json()["view"]["eligible_actions"]}

    for action_id in [
        "look_around", "pick_up_journal",
        "head_to_town", "wander_home", "walk_to_town",
        "walk_to_meadow", "back_into_town_from_meadow",
        "follow_forest_path", "back_into_town_from_forest",
        "stroll_to_beach", "back_into_town_from_beach",
        "wander_home",
    ]:
        assert action_id in offered, (action_id, offered)
        response = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert response.status_code == 200, response.text
        offered = {a["action_id"] for a in response.json()["view"]["eligible_actions"]}

    state = client.get(f"/v1/sessions/{session_id}").json()["state"]
    assert state["current_place_id"] == "cottage_home"
    from idle_chapters.persistence.state_store import StateStore

    visits = StateStore().get_state(session_id).visit_counts
    assert visits == {"cottage_home": 3, "town": 5, "meadow": 1, "forest": 1, "beach": 1}
    assert state["inventory"]["journal"] == 1
    assert state["inventory"]["bag"] == 1
    assert "walk_to_town" in offered
    assert not offered & {"look_around", "head_to_town"}


def test_leaving_early_keeps_tea_and_the_journal_for_later(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    session_id = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()["session_id"]
    for action_id in ["look_around", "head_to_town", "wander_home"]:
        response = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert response.status_code == 200, response.text

    offered = {a["action_id"] for a in response.json()["view"]["eligible_actions"]}
    assert {"make_tea", "pick_up_journal"} <= offered


def test_look_around_waits_after_tea_and_the_journal(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    session_id = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()["session_id"]
    for action_id in ["make_tea", "pick_up_journal"]:
        response = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert response.status_code == 200, response.text

    assert "look_around" in {a["action_id"] for a in response.json()["view"]["eligible_actions"]}


def test_docs_mark_the_projection_the_server_defaults_to() -> None:
    from idle_chapters.api.server import create_app

    summaries = []

    def walk(node) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("summary"), str) and "projection" in node["summary"].lower():
                summaries.append(node["summary"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(create_app().openapi())
    defaults = [s for s in summaries if "(default)" in s]
    assert defaults
    assert all(s.startswith("Developer") for s in defaults), defaults
