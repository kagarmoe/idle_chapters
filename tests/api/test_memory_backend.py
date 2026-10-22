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


def test_health_reports_the_deployed_commit(monkeypatch) -> None:
    # ic-ship's smoke waits until production reports the merged commit.
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import create_app

    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "abc123")
    assert TestClient(create_app()).get("/health").json() == {"status": "ok", "commit": "abc123"}
    monkeypatch.delenv("VERCEL_GIT_COMMIT_SHA")
    assert TestClient(create_app()).get("/health").json() == {"status": "ok", "commit": None}


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


def test_every_sub_place_can_be_visited_and_left(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    session_id = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()["session_id"]
    from idle_chapters.content.repo import ContentRepo

    results = {action_id: action["result"] for action_id, action in ContentRepo().actions_by_id.items()}
    pages = []

    def take(action_id: str) -> set[str]:
        response = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert response.status_code == 200, response.text
        pages.append(response.json()["journal_page"]["body"])
        return {a["action_id"] for a in response.json()["view"]["eligible_actions"]}

    def place() -> str:
        return client.get(f"/v1/sessions/{session_id}").json()["state"]["current_place_id"]

    take("look_around")
    offered = take("head_to_town")
    zones = [
        ("town", None, None, "back_to_town_centre", {
            "visit_bakery": "town_bakery", "visit_mercantile": "town_store", "visit_street_vendor": "town_vendor"}),
        ("forest", "follow_forest_path", "back_into_town_from_forest", "back_to_forest", {
            "walk_forest_trail": "forest_trail", "visit_tiny_castle": "forest_castle", "visit_waterfall": "forest_waterfall"}),
        ("meadow", "walk_to_meadow", "back_into_town_from_meadow", "back_to_meadow", {
            "walk_shepherds_path": "meadow_path", "stroll_up_the_hill": "meadow_hill", "visit_shrine": "meadow_shrine"}),
        ("beach", "stroll_to_beach", "back_into_town_from_beach", "back_to_beach", {
            "stroll_boardwalk": "beach_boardwalk", "visit_tidepools": "beach_tidepools", "walk_out_on_pier": "beach_pier"}),
    ]
    for root, way_out, way_back, back, sub_places in zones:
        if way_out:
            offered = take(way_out)
        assert place() == root
        assert back not in offered
        for action_id, sub_place in sub_places.items():
            assert action_id in offered, (action_id, offered)
            offered = take(action_id)
            assert place() == sub_place
            assert results[action_id] in pages[-1], (action_id, pages[-1])
            assert {back, "wander_home"} <= offered, offered
            offered = take(back)
            assert place() == root
        if way_back:
            offered = take(way_back)


def test_the_bakery_offers_a_cinnamon_roll_whenever_you_like(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server
    from idle_chapters.content.repo import ContentRepo

    client = TestClient(server)
    actions = ContentRepo().actions_by_id
    session_id = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()["session_id"]

    def take(action_id: str) -> set[str]:
        response = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert response.status_code == 200, response.text
        assert actions[action_id]["result"] in response.json()["journal_page"]["body"]
        return {a["action_id"] for a in response.json()["view"]["eligible_actions"]}

    for action_id in ["look_around", "head_to_town"]:
        take(action_id)
    offered = take("visit_bakery")
    for action_id, next_offer in [
        ("enjoy_a_cinnamon_roll", "linger_at_the_counter"),
        ("linger_at_the_counter", "enjoy_a_cinnamon_roll"),
        ("enjoy_a_cinnamon_roll", "linger_at_the_counter"),
    ]:
        assert {action_id, "back_to_town_centre"} <= offered, offered
        offered = take(action_id)
        assert next_offer in offered, offered

    state = client.get(f"/v1/sessions/{session_id}").json()["state"]
    assert state["inventory"]["cinnamon_roll"] == 2


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


def test_coming_home_settles_in_rather_than_waking_again(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    created = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()
    session_id = created["session_id"]
    assert created["view"]["scene_id"] == "cottage_wake_v1"

    def take(action_id: str) -> dict:
        response = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert response.status_code == 200, response.text
        return response.json()["view"]

    take("head_to_town")
    home = take("wander_home")
    assert home["scene_id"] == "cottage_home_return_v1"
    assert "sit_by_the_fire" in {a["action_id"] for a in home["eligible_actions"]}
    # The walk's page also tells the arrival, so settling in needs no extra /enter.
    assert "You take the long way home" in home["prompt"]
    assert "You ease the door shut behind you." in home["prompt"]
    assert "bed" not in take("look_around")["prompt"]


def test_get_session_resumes_the_view_it_left(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    created = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()
    session_id = created["session_id"]

    def assert_resumes(step: dict) -> None:
        assert step["view"]["eligible_actions"]
        resumed = client.get(f"/v1/sessions/{session_id}")
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["view"]["eligible_actions"] == step["view"]["eligible_actions"]
        assert resumed.json()["journal_page"] == step["journal_page"]

    assert_resumes(created)
    # After an authored action, then in a procedural place (town has no authored scene).
    for action_id in ("look_around", "head_to_town"):
        step = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert step.status_code == 200, step.text
        assert_resumes(step.json())


def test_free_text_does_each_thing_in_turn_until_you_leave(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)

    def say(text: str) -> tuple[dict, list]:
        session_id = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()["session_id"]
        response = client.post(f"/v1/sessions/{session_id}/intent", json={"input": text})
        assert response.status_code == 200, response.text
        return response.json(), client.get(f"/v1/sessions/{session_id}/journal").json()

    step, pages = say("I'd like a cup of tea, then I'll pick up the journal.")
    assert len(pages) == 3
    assert "You lift the journal from the table." in step["view"]["prompt"]

    # Leaving ends the turn: nothing after "town" happens at the cottage or in town.
    step, pages = say("head to town and then make tea")
    assert len(pages) == 2
    assert "wander_home" in {a["action_id"] for a in step["view"]["eligible_actions"]}


def test_walking_into_the_bakery_meets_whoever_is_there(monkeypatch) -> None:
    from idle_chapters.persistence import mongo

    monkeypatch.setenv("MONGO_URL", "memory://")
    monkeypatch.setattr(mongo, "_CLIENT", None)

    from idle_chapters.api.server import server

    client = TestClient(server)
    session_id = client.post("/v1/sessions", json={"place_id": "cottage_home"}).json()["session_id"]
    for action_id in ("head_to_town", "visit_bakery"):
        step = client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})
        assert step.status_code == 200, step.text
    view = step.json()["view"]

    assert {"Elin the Baker", "Moss"} <= set(view["visible_npcs"])
    assert "Elin the Baker" in view["prompt"] or "Moss" in view["prompt"]
    resumed = client.get(f"/v1/sessions/{session_id}").json()
    assert resumed["view"]["visible_npcs"] == view["visible_npcs"]
    assert sum(resumed["state"]["seen_interactions"].values()) >= 1
