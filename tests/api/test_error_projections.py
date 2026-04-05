import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from idle_chapters.api.deps import get_session_service
from idle_chapters.api.routers import sessions
from idle_chapters.services.errors import GameError


def _make_test_app():
    """Build a minimal FastAPI app with the sessions router and GameError handler."""
    from types import SimpleNamespace

    from idle_chapters.domain.engine import Engine
    from idle_chapters.services.session_service import SessionService

    app = FastAPI()
    app.include_router(sessions.router)

    @app.exception_handler(GameError)
    async def handle_game_error(request: Request, exc: GameError) -> JSONResponse:
        projection = request.headers.get("Accept-Projection", "player")
        if projection == "developer":
            body = exc.project_developer()
        else:
            body = exc.project_player()
        return JSONResponse(status_code=exc.http_status, content=body)

    # Minimal stub repo / stores
    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={},
        scenes_by_id={},
        actions_by_id={},
        journal_templates_by_entry_type={},
        journal_templates_by_id={},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )

    class StubStateStore:
        def get_state(self, session_id):
            return None
        def upsert_state(self, session_id, state):
            pass

    class StubJournalStore:
        def list_pages(self, session_id):
            return []
        def get_page(self, session_id, page_id):
            return None
        def append_page(self, session_id, page):
            pass

    class StubEventStore:
        def append_event(self, session_id, event):
            pass
        def list_events(self, session_id):
            return []

    def _override_service():
        return SessionService(
            repo=repo,
            engine=Engine(),
            state_store=StubStateStore(),
            journal_store=StubJournalStore(),
            event_store=StubEventStore(),
        )

    app.dependency_overrides[get_session_service] = _override_service
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = _make_test_app()
    return TestClient(app)


class TestPlayerProjection:
    def test_session_not_found_returns_rfc9457_player(self, client):
        resp = client.get("/v1/sessions/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert body["type"] == "urn:idle-chapters:error:session_not_found"
        assert body["status"] == 404
        assert "title" in body
        # Player projection must NOT include extension members
        assert "effect" not in body
        assert "recovery" not in body
        assert "signal" not in body

    def test_default_projection_is_player(self, client):
        resp = client.get("/v1/sessions/nonexistent")
        body = resp.json()
        assert set(body.keys()) == {"type", "title", "status"}


class TestDeveloperProjection:
    def test_session_not_found_returns_full_rfc9457(self, client):
        resp = client.get(
            "/v1/sessions/nonexistent",
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["type"] == "urn:idle-chapters:error:session_not_found"
        assert body["title"] == "Session Not Found"
        assert body["status"] == 404
        assert "WHAT" in body["detail"]
        assert "MEANS" in body["detail"]
        assert "DO" in body["detail"]
        assert body["instance"].startswith("urn:idle-chapters:occurrence:")
        assert body["effect"] == "none"
        assert body["recovery"] == "terminal"
        assert body["signal"] == "NOTICE"
        assert "session_id" in body["context"]
