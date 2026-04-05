import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from idle_chapters.api.routers import players, journal
from idle_chapters.api.deps import get_db
from idle_chapters.services.errors import GameError


def _make_test_app():
    app = FastAPI()
    app.include_router(players.router)
    app.include_router(journal.router)

    @app.exception_handler(GameError)
    async def handle_game_error(request: Request, exc: GameError) -> JSONResponse:
        projection = request.headers.get("Accept-Projection", "player")
        if projection == "developer":
            body = exc.project_developer()
        else:
            body = exc.project_player()
        return JSONResponse(status_code=exc.http_status, content=body)

    # Stub DB that returns None for all finds
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=MagicMock(find_one=MagicMock(return_value=None)))

    app.dependency_overrides[get_db] = lambda: mock_db
    return app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(_make_test_app())


def test_get_player_not_found_returns_rfc9457(client):
    resp = client.get("/v1/players/nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:idle-chapters:error:player_not_found"
    assert body["status"] == 404
    assert set(body.keys()) == {"type", "title", "status"}


def test_get_player_not_found_developer_projection(client):
    resp = client.get(
        "/v1/players/nonexistent",
        headers={"Accept-Projection": "developer"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:idle-chapters:error:player_not_found"
    assert body["signal"] == "NOTICE"
    assert "WHAT" in body["detail"]


def test_get_inventory_player_not_found(client):
    resp = client.get("/v1/players/nonexistent/inventory")
    assert resp.status_code == 404
    assert resp.json()["type"] == "urn:idle-chapters:error:player_not_found"


def test_get_journal_player_not_found(client):
    resp = client.get("/v1/players/nonexistent/journal")
    assert resp.status_code == 404
    assert resp.json()["type"] == "urn:idle-chapters:error:player_not_found"
