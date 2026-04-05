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
from idle_chapters.api.models import (
    SessionCreateResponse,
    SessionGetResponse,
    StepResponse,
    PlayerResponse,
)
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
        try:
            c.admin.command("ping")
            return True
        finally:
            c.close()
    except Exception:
        return False


# Skip the entire module when MongoDB is unreachable.
# CI sets MONGO_URL; locally we probe the default port as a fallback.
pytestmark = pytest.mark.skipif(
    not os.environ.get("MONGO_URL", "").strip() and not _mongo_available(),
    reason="MongoDB not available (set MONGO_URL or run mongod locally)",
)


def _example_keys(responses_dict: dict, status_code: int, example_name: str) -> set[str]:
    """Extract the keys from a named example in a responses dict."""
    return set(
        responses_dict[status_code]["content"]["application/json"]["examples"][example_name]["value"].keys()
    )


def _compare_shape(label: str, actual, example, errors: list[str], path: str = "") -> None:
    """Recursively compare the shape (keys and value types) of actual vs example."""
    if isinstance(example, dict) and isinstance(actual, dict):
        actual_keys = set(actual.keys())
        example_keys = set(example.keys())
        extra = actual_keys - example_keys
        missing = example_keys - actual_keys
        if extra:
            errors.append(f"{label}{path}: response has fields not in example: {extra}")
        if missing:
            errors.append(f"{label}{path}: example has fields not in response: {missing}")
        for key in actual_keys & example_keys:
            _compare_shape(label, actual[key], example[key], errors, f"{path}.{key}")
    elif isinstance(example, list) and isinstance(actual, list):
        # Check first element shape if both non-empty
        if actual and example:
            _compare_shape(label, actual[0], example[0], errors, f"{path}[0]")
    elif type(actual).__name__ != type(example).__name__:
        # Allow None vs any type (None is valid for optional fields)
        if actual is not None and example is not None:
            errors.append(
                f"{label}{path}: type mismatch: response is {type(actual).__name__}, "
                f"example is {type(example).__name__}"
            )


@pytest.fixture(scope="module")
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def openapi_examples():
    return {
        "SessionCreateResponse": SessionCreateResponse.model_config["json_schema_extra"]["example"],
        "SessionGetResponse": SessionGetResponse.model_config["json_schema_extra"]["example"],
        "StepResponse": StepResponse.model_config["json_schema_extra"]["example"],
        "PlayerResponse": PlayerResponse.model_config["json_schema_extra"]["example"],
    }


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

    def test_create_session_fields(self, client, openapi_examples):
        resp = client.post("/v1/sessions", json={"place_id": "cottage_home"})
        assert resp.status_code == 200
        errs: list[str] = []
        _compare_shape("SessionCreateResponse", resp.json(), openapi_examples["SessionCreateResponse"], errs)
        assert errs == [], "\n".join(errs)

    def test_get_session_fields(self, client, session_id, openapi_examples):
        resp = client.get(f"/v1/sessions/{session_id}")
        assert resp.status_code == 200
        errs: list[str] = []
        _compare_shape("SessionGetResponse", resp.json(), openapi_examples["SessionGetResponse"], errs)
        assert errs == [], "\n".join(errs)

    def test_get_session_state_fields(self, client, session_id, openapi_examples):
        resp = client.get(f"/v1/sessions/{session_id}")
        assert resp.status_code == 200
        errs: list[str] = []
        _compare_shape(
            "SessionGetResponse.state",
            resp.json()["state"],
            openapi_examples["SessionGetResponse"]["state"],
            errs,
        )
        assert errs == [], "\n".join(errs)

    def test_enter_fields(self, client, session_id, openapi_examples):
        resp = client.post(f"/v1/sessions/{session_id}/enter")
        assert resp.status_code == 200
        errs: list[str] = []
        _compare_shape("StepResponse", resp.json(), openapi_examples["StepResponse"], errs)
        assert errs == [], "\n".join(errs)

    def test_create_player_fields(self, client, openapi_examples):
        resp = client.post("/v1/players", json={"display_name": "FieldTest"})
        assert resp.status_code == 200
        errs: list[str] = []
        _compare_shape("PlayerResponse", resp.json(), openapi_examples["PlayerResponse"], errs)
        assert errs == [], "\n".join(errs)

    def test_get_player_fields(self, client, player_id, openapi_examples):
        resp = client.get(f"/v1/players/{player_id}")
        assert resp.status_code == 200
        errs: list[str] = []
        _compare_shape("PlayerResponse", resp.json(), openapi_examples["PlayerResponse"], errs)
        assert errs == [], "\n".join(errs)


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

    def test_action_not_eligible(self, client, session_id):
        resp = client.post(
            f"/v1/sessions/{session_id}/action",
            json={"action_id": "nonexistent_action"},
        )
        assert resp.status_code == 409
        actual = set(resp.json().keys())
        expected = _example_keys(ACTION_NOT_ELIGIBLE_RESPONSES, 409, "player")
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

    def test_action_not_eligible(self, client, session_id):
        resp = client.post(
            f"/v1/sessions/{session_id}/action",
            json={"action_id": "nonexistent_action"},
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 409
        actual = set(resp.json().keys())
        expected = _example_keys(ACTION_NOT_ELIGIBLE_RESPONSES, 409, "developer")
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
