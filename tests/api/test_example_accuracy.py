"""Verify that OpenAPI response examples match actual API responses.

These tests call real endpoints (with real MongoDB) and compare the
fields in the response to the fields in the hand-written examples
from error_helpers.py and models.py. This catches drift between
what the docs claim and what the API returns.

Requires: MongoDB running on localhost:27017
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from idle_chapters.api.server import create_app
from idle_chapters.api.routers.error_helpers import (
    ACTION_NOT_ELIGIBLE_RESPONSES,
    INTENT_NO_MATCH_RESPONSES,
    JOURNAL_PAGE_404_RESPONSES,
    PLAYER_NOT_FOUND_RESPONSES,
    SESSION_NOT_FOUND_RESPONSES,
)


def _mongo_available() -> bool:
    try:
        from pymongo import MongoClient

        c = MongoClient("localhost", 27017, serverSelectionTimeoutMS=1000)
        c.admin.command("ping")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not os.environ.get("MONGO_URL", "").strip() and not _mongo_available(),
    reason="MongoDB not available",
)


def _example_keys(responses_dict: dict, status_code: int, example_name: str) -> set[str]:
    """Extract the keys from a named example in a responses dict."""
    return set(
        responses_dict[status_code]["content"]["application/json"]["examples"][example_name]["value"].keys()
    )


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def session_id(client):
    resp = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    assert resp.status_code == 200
    return resp.json()["session_id"]


@pytest.fixture(scope="module")
def player_id(client):
    resp = client.post("/v1/players", json={"display_name": "Test", "pronouns_key": "they/them"})
    assert resp.status_code == 200
    return resp.json()["player_id"]


# --- Success response field checks ---


class TestSuccessExamples:
    """Verify success response fields match Pydantic model examples."""

    def test_create_session_fields(self, client):
        resp = client.post("/v1/sessions", json={"place_id": "cottage_home"})
        assert resp.status_code == 200
        actual = set(resp.json().keys())
        spec = create_app().openapi()
        example = set(spec["components"]["schemas"]["SessionCreateResponse"]["example"].keys())
        assert actual == example, f"actual {actual} != example {example}"

    def test_get_session_fields(self, client, session_id):
        resp = client.get(f"/v1/sessions/{session_id}")
        assert resp.status_code == 200
        actual = set(resp.json().keys())
        spec = create_app().openapi()
        example = set(spec["components"]["schemas"]["SessionGetResponse"]["example"].keys())
        assert actual == example

    def test_get_session_state_fields(self, client, session_id):
        resp = client.get(f"/v1/sessions/{session_id}")
        actual = set(resp.json()["state"].keys())
        spec = create_app().openapi()
        example = set(spec["components"]["schemas"]["SessionGetResponse"]["example"]["state"].keys())
        assert actual == example, f"state: actual {actual} != example {example}"

    def test_enter_fields(self, client, session_id):
        resp = client.post(f"/v1/sessions/{session_id}/enter")
        assert resp.status_code == 200
        actual = set(resp.json().keys())
        spec = create_app().openapi()
        example = set(spec["components"]["schemas"]["StepResponse"]["example"].keys())
        assert actual == example

    def test_create_player_fields(self, client):
        resp = client.post("/v1/players", json={"display_name": "FieldTest"})
        assert resp.status_code == 200
        actual = set(resp.json().keys())
        spec = create_app().openapi()
        example = set(spec["components"]["schemas"]["PlayerResponse"]["example"].keys())
        assert actual == example

    def test_get_player_fields(self, client, player_id):
        resp = client.get(f"/v1/players/{player_id}")
        assert resp.status_code == 200
        actual = set(resp.json().keys())
        spec = create_app().openapi()
        example = set(spec["components"]["schemas"]["PlayerResponse"]["example"].keys())
        assert actual == example


# --- Error response field checks (player projection) ---


class TestErrorExamplesPlayerProjection:
    """Verify error response fields match hand-written examples (player projection)."""

    def test_session_not_found(self, client):
        resp = client.get("/v1/sessions/nonexistent")
        assert resp.status_code == 404
        actual = set(resp.json().keys())
        expected = _example_keys(SESSION_NOT_FOUND_RESPONSES, 404, "player")
        assert actual == expected, f"actual {actual} != example {expected}"

    def test_player_not_found(self, client):
        resp = client.get("/v1/players/nonexistent")
        assert resp.status_code == 404
        actual = set(resp.json().keys())
        expected = _example_keys(PLAYER_NOT_FOUND_RESPONSES, 404, "player")
        assert actual == expected

    def test_intent_no_match(self, client, session_id):
        resp = client.post(
            f"/v1/sessions/{session_id}/intent",
            json={"input": "fly to the moon"},
        )
        assert resp.status_code == 422
        actual = set(resp.json().keys())
        expected = _example_keys(INTENT_NO_MATCH_RESPONSES, 422, "player")
        assert actual == expected


# --- Error response field checks (developer projection) ---


class TestErrorExamplesDeveloperProjection:
    """Verify error response fields match hand-written examples (developer projection)."""

    def test_session_not_found(self, client):
        resp = client.get(
            "/v1/sessions/nonexistent",
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 404
        actual = set(resp.json().keys())
        expected = _example_keys(SESSION_NOT_FOUND_RESPONSES, 404, "developer")
        assert actual == expected, f"actual {actual} != example {expected}"

    def test_player_not_found(self, client):
        resp = client.get(
            "/v1/players/nonexistent",
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 404
        actual = set(resp.json().keys())
        expected = _example_keys(PLAYER_NOT_FOUND_RESPONSES, 404, "developer")
        assert actual == expected

    def test_intent_no_match(self, client, session_id):
        resp = client.post(
            f"/v1/sessions/{session_id}/intent",
            json={"input": "fly to the moon"},
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 422
        actual = set(resp.json().keys())
        expected = _example_keys(INTENT_NO_MATCH_RESPONSES, 422, "developer")
        assert actual == expected

    def test_journal_page_not_found(self, client, session_id):
        resp = client.get(
            f"/v1/sessions/{session_id}/journal/nonexistent",
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 404
        actual = set(resp.json().keys())
        expected = _example_keys(
            JOURNAL_PAGE_404_RESPONSES, 404, "journal_page_not_found_developer",
        )
        assert actual == expected
