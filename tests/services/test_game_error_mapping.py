from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from idle_chapters.domain.engine import Engine
from idle_chapters.domain.errors import (
    ActionNotEligible,
    InsufficientInventory,
    IntentNoMatch,
    SessionNotFound,
)
from idle_chapters.domain.state import PlayerState
from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.services.session_service import SessionService


def _make_service(state=None, engine=None):
    state_store = MagicMock()
    state_store.get_state.return_value = state
    journal_store = MagicMock()
    event_store = MagicMock()
    repo = SimpleNamespace(
        places_by_id={},
        scenes_by_place_id={},
        actions_by_id={},
        journal_templates_by_entry_type={},
        journal_templates_by_id={},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )
    return SessionService(
        repo=repo,
        engine=engine or Engine(),
        state_store=state_store,
        journal_store=journal_store,
        event_store=event_store,
    )


def test_session_not_found_maps_to_game_error():
    service = _make_service(state=None)
    with pytest.raises(GameError) as exc_info:
        service.perform_action("missing-id", "some_action")
    err = exc_info.value
    assert err.kind == ErrorKind.SESSION_NOT_FOUND
    assert err.effect == Effect.NONE
    assert err.recovery == Recovery.TERMINAL
    assert err.context["session_id"] == "missing-id"
    assert "WHAT" in err.detail
    assert "MEANS" in err.detail
    assert "DO" in err.detail


def test_action_not_eligible_maps_to_game_error():
    state = PlayerState(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
    )
    engine = MagicMock()
    engine.step.side_effect = ActionNotEligible(
        action_id="nonexistent_action",
        session_id="s1",
        unmet_conditions=["action not found in current scene"],
    )
    service = _make_service(state=state, engine=engine)
    with pytest.raises(GameError) as exc_info:
        service.perform_action("s1", "nonexistent_action")
    err = exc_info.value
    assert err.kind == ErrorKind.ACTION_NOT_ELIGIBLE
    assert err.effect == Effect.NONE
    assert err.recovery == Recovery.CORRECTABLE


def test_intent_no_match_maps_to_game_error():
    state = PlayerState(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
    )
    engine = MagicMock()
    # submit_intent first calls engine.step with "enter" to get choices
    engine.step.return_value = MagicMock(
        journal_page=None, new_state=state, debug={},
        choices=[{"action_id": "make_tea", "label": "Make tea"}],
    )
    service = _make_service(state=state, engine=engine)
    with pytest.raises(GameError) as exc_info:
        service.submit_intent("s1", "fly to the moon")
    err = exc_info.value
    assert err.kind == ErrorKind.INTENT_NO_MATCH
    assert err.effect == Effect.NONE
    assert err.recovery == Recovery.CORRECTABLE
    assert err.context["input"] == "fly to the moon"


def test_persistence_failure_maps_to_partial_effect():
    state = PlayerState(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
    )
    engine = MagicMock()
    engine.step.return_value = MagicMock(
        journal_page=None, new_state=state, debug={}, choices=[],
    )
    service = _make_service(state=state, engine=engine)
    service._state_store.upsert_state.side_effect = Exception("DB down")
    with pytest.raises(GameError) as exc_info:
        service.enter("s1")
    err = exc_info.value
    assert err.kind == ErrorKind.PERSISTENCE_FAILURE
    assert err.effect == Effect.PARTIAL
    assert err.recovery == Recovery.RETRYABLE
