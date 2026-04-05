from __future__ import annotations

from types import SimpleNamespace

import pytest

from idle_chapters.domain.engine import Engine
from idle_chapters.domain.state import PlayerState


# -- Stub stores (in-memory, no MongoDB) --


class StubStateStore:
    def __init__(self):
        self._data: dict[str, PlayerState] = {}

    def upsert_state(self, session_id: str, state: PlayerState) -> None:
        self._data[session_id] = state

    def get_state(self, session_id: str) -> PlayerState | None:
        return self._data.get(session_id)


class StubJournalStore:
    def __init__(self):
        self._pages: dict[str, list[dict]] = {}

    def append_page(self, session_id: str, page: dict) -> None:
        self._pages.setdefault(session_id, []).append(page)

    def list_pages(self, session_id: str) -> list[dict]:
        return self._pages.get(session_id, [])

    def get_page(self, session_id: str, page_id: str) -> dict | None:
        for p in self._pages.get(session_id, []):
            if p.get("page_id") == page_id:
                return p
        return None


class StubEventStore:
    def __init__(self):
        self._events: dict[str, list[dict]] = {}

    def append_event(self, session_id: str, event: dict) -> None:
        self._events.setdefault(session_id, []).append(event)

    def list_events(self, session_id: str) -> list[dict]:
        return self._events.get(session_id, [])


# -- Mock repo with an authored scene that has choices --

TEMPLATE = {
    "template_id": "t1",
    "entry_type": "tea",
    "prompt": "What softened today?",
    "structure": ["A moment passed quietly."],
    "tags": [],
}


def _make_repo():
    """Build a mock repo with a scene graph that supports enter + choose."""
    return SimpleNamespace(
        places_by_id={
            "cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"},
        },
        scenes_by_place_id={
            "cottage_home": [
                {
                    "scene_id": "scene_wake",
                    "place_id": "cottage_home",
                    "entry_node": "n_start",
                    "nodes": [
                        {
                            "node_id": "n_start",
                            "action_ref": "wake_up",
                            "choices": ["n_look", "n_tea"],
                        },
                        {
                            "node_id": "n_look",
                            "action_ref": "look_around",
                            "choices": [],
                        },
                        {
                            "node_id": "n_tea",
                            "action_ref": "make_tea",
                            "choices": [],
                        },
                    ],
                }
            ]
        },
        scenes_by_id={
            "scene_wake": {
                "scene_id": "scene_wake",
                "place_id": "cottage_home",
                "entry_node": "n_start",
                "nodes": [
                    {
                        "node_id": "n_start",
                        "action_ref": "wake_up",
                        "choices": ["n_look", "n_tea"],
                    },
                    {
                        "node_id": "n_look",
                        "action_ref": "look_around",
                        "choices": [],
                    },
                    {
                        "node_id": "n_tea",
                        "action_ref": "make_tea",
                        "choices": [],
                    },
                ],
            }
        },
        actions_by_id={
            "wake_up": {
                "action_id": "wake_up",
                "label": "Wake up",
                "effects": {},
                "result": "You stir awake.",
            },
            "look_around": {
                "action_id": "look_around",
                "label": "Look around",
                "effects": {},
                "result": "Sunlight fills the room.",
                "intent_signature": {
                    "phrases": ["look around"],
                    "keywords": ["look"],
                },
            },
            "make_tea": {
                "action_id": "make_tea",
                "label": "Make tea",
                "effects": {"set_flags": ["made_tea"]},
                "result": "The kettle hums.",
                "tags": ["tea"],
                "intent_signature": {
                    "phrases": ["make tea", "brew tea"],
                    "keywords": ["tea"],
                },
            },
        },
        journal_templates_by_entry_type={"tea": [TEMPLATE]},
        journal_templates_by_id={"t1": TEMPLATE},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )


@pytest.fixture
def repo():
    return _make_repo()


@pytest.fixture
def stores():
    return StubStateStore(), StubJournalStore(), StubEventStore()


@pytest.fixture
def service(repo, stores):
    from idle_chapters.services.session_service import SessionService

    state_store, journal_store, event_store = stores
    return SessionService(
        repo=repo,
        engine=Engine(),
        state_store=state_store,
        journal_store=journal_store,
        event_store=event_store,
    )


# -- SessionService unit tests --


def test_create_session_returns_session_id_and_journal_page(service) -> None:
    session_id, result = service.create_session()
    assert session_id is not None
    assert len(session_id) > 0
    assert result.journal_page is not None
    assert result.new_state.current_place_id == "cottage_home"


def test_create_session_persists_state(service, stores) -> None:
    state_store, journal_store, _ = stores
    session_id, _ = service.create_session()
    loaded = state_store.get_state(session_id)
    assert loaded is not None
    assert loaded.current_place_id == "cottage_home"
    assert journal_store.list_pages(session_id)


def test_create_session_returns_choices(service) -> None:
    _, result = service.create_session()
    assert len(result.choices) == 2
    action_ids = {c["action_id"] for c in result.choices}
    assert "look_around" in action_ids
    assert "make_tea" in action_ids


def test_perform_action_returns_journal_page(service) -> None:
    session_id, result = service.create_session()
    action_id = result.choices[0]["action_id"]
    step_result = service.perform_action(session_id, action_id)
    assert step_result.journal_page is not None


def test_get_session_returns_state(service) -> None:
    session_id, _ = service.create_session()
    state = service.get_session(session_id)
    assert state is not None
    assert state.session_id == session_id
    assert state.current_place_id == "cottage_home"


def test_get_session_missing_returns_none(service) -> None:
    assert service.get_session("nonexistent") is None


def test_enter_returns_choices(service) -> None:
    session_id, _ = service.create_session()
    result = service.enter(session_id)
    assert result.choices is not None
    assert len(result.choices) == 2
    assert result.journal_page is not None


def test_submit_intent_matches_action(service) -> None:
    session_id, _ = service.create_session()
    step_result = service.submit_intent(session_id, "look around")
    assert step_result.journal_page is not None


def test_state_persists_across_calls(service, stores) -> None:
    state_store, _, _ = stores
    session_id, result = service.create_session()
    action_id = result.choices[0]["action_id"]
    service.perform_action(session_id, action_id)
    loaded = state_store.get_state(session_id)
    assert loaded is not None


def test_journal_list_returns_pages(service, stores) -> None:
    _, journal_store, _ = stores
    session_id, _ = service.create_session()
    pages = journal_store.list_pages(session_id)
    assert len(pages) >= 1


def test_journal_get_missing_returns_none(service, stores) -> None:
    _, journal_store, _ = stores
    session_id, _ = service.create_session()
    assert journal_store.get_page(session_id, "nonexistent") is None


# -- HTTP integration tests --


def _make_test_app(repo, stores):
    """Build a FastAPI app with dependency overrides for testing."""
    from fastapi import FastAPI

    from idle_chapters.api.deps import get_session_service
    from idle_chapters.api.routers import sessions

    app = FastAPI()
    app.include_router(sessions.router)

    state_store, journal_store, event_store = stores

    def _override_service():
        from idle_chapters.services.session_service import SessionService as _SS

        return _SS(
            repo=repo,
            engine=Engine(),
            state_store=state_store,
            journal_store=journal_store,
            event_store=event_store,
        )

    app.dependency_overrides[get_session_service] = _override_service
    return app


try:
    import httpx  # noqa: F401

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


@pytest.fixture
def client(repo, stores):
    pytest.importorskip("httpx", reason="httpx required for HTTP tests")
    from fastapi.testclient import TestClient

    app = _make_test_app(repo, stores)
    return TestClient(app)


def test_http_create_session(client) -> None:
    response = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "view" in data
    assert "journal_page" in data


def test_http_get_session(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.get(f"/v1/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "state" in data


def test_http_get_session_not_found(client) -> None:
    response = client.get("/v1/sessions/nonexistent")
    assert response.status_code == 404


def test_http_enter(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.post(f"/v1/sessions/{session_id}/enter")
    assert response.status_code == 200
    data = response.json()
    assert "view" in data
    assert "choices" in data
    assert len(data["choices"]) == 2


def test_http_action(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    enter = client.post(f"/v1/sessions/{session_id}/enter")
    choices = enter.json()["choices"]
    action_id = choices[0]["action_id"]
    response = client.post(
        f"/v1/sessions/{session_id}/action",
        json={"action_id": action_id},
    )
    assert response.status_code == 200
    assert "journal_page" in response.json()


def test_http_intent(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.post(
        f"/v1/sessions/{session_id}/intent",
        json={"input": "look around"},
    )
    assert response.status_code == 200


def test_http_journal_list(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.get(f"/v1/sessions/{session_id}/journal")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_http_state_persists_across_calls(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]

    enter = client.post(f"/v1/sessions/{session_id}/enter")
    choices = enter.json()["choices"]
    action_id = choices[0]["action_id"]
    client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})

    state_response = client.get(f"/v1/sessions/{session_id}")
    assert state_response.status_code == 200
    assert state_response.json()["session_id"] == session_id
