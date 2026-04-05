import pytest

from idle_chapters.domain.errors import (
    SessionNotFound,
    ActionNotEligible,
    IntentNoMatch,
    InsufficientInventory,
    InvalidLocation,
    SceneNotAvailable,
)


def test_session_not_found_carries_session_id():
    err = SessionNotFound(session_id="abc-123")
    assert err.session_id == "abc-123"
    assert "abc-123" in str(err)


def test_action_not_eligible_carries_context():
    err = ActionNotEligible(
        action_id="gather_herbs",
        session_id="abc-123",
        unmet_conditions=["flags_set: visited_garden"],
    )
    assert err.action_id == "gather_herbs"
    assert err.session_id == "abc-123"
    assert err.unmet_conditions == ["flags_set: visited_garden"]


def test_intent_no_match_carries_input_and_actions():
    err = IntentNoMatch(
        input_text="dance around",
        available_actions=["brew tea", "rest"],
    )
    assert err.input_text == "dance around"
    assert err.available_actions == ["brew tea", "rest"]


def test_insufficient_inventory_carries_amounts():
    err = InsufficientInventory(
        item_id="chamomile",
        required=3,
        available=1,
    )
    assert err.item_id == "chamomile"
    assert err.required == 3
    assert err.available == 1


def test_invalid_location_carries_location_id():
    err = InvalidLocation(location_id="nowhere")
    assert err.location_id == "nowhere"


def test_scene_not_available_carries_session_id():
    err = SceneNotAvailable(session_id="abc-123")
    assert err.session_id == "abc-123"


def test_all_exceptions_are_exceptions():
    for cls in [
        SessionNotFound,
        ActionNotEligible,
        IntentNoMatch,
        InsufficientInventory,
        InvalidLocation,
        SceneNotAvailable,
    ]:
        assert issubclass(cls, Exception)
