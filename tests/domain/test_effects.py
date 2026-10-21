import pytest

from idle_chapters.domain.effects import apply_effects
from idle_chapters.domain.errors import InsufficientInventory
from idle_chapters.domain.state import PlayerState


def test_apply_effects_updates_state() -> None:
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={"item_1": 1},
        flags=set(),
        time_tick=0,
    )

    effects = {
        "add_items": {"item_1": 1, "item_2": 2},
        "remove_items": {"item_1": 1},
        "set_flags": ["flag_a"],
        "clear_flags": ["flag_b"],
    }

    new_state = apply_effects(state, effects)
    assert new_state.inventory["item_1"] == 1
    assert new_state.inventory["item_2"] == 2
    assert "flag_a" in new_state.flags


def test_apply_effects_prevents_negative_inventory() -> None:
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={"item_1": 0},
        flags=set(),
        time_tick=0,
    )

    effects = {"remove_items": {"item_1": 1}}

    with pytest.raises(InsufficientInventory) as exc_info:
        apply_effects(state, effects)
    assert exc_info.value.item_id == "item_1"
    assert exc_info.value.required == 1
    assert exc_info.value.available == 0


def _at(place: str, visits: dict[str, int]) -> PlayerState:
    return PlayerState(session_id="s", current_place_id=place, inventory={}, flags=set(), time_tick=0, visit_counts=visits)


def test_move_to_a_new_place_counts_an_arrival() -> None:
    state = _at("home", {"home": 1, "town": 1})
    moved = apply_effects(state, {"move_to": "town"})
    assert moved.visit_counts == {"home": 1, "town": 2}
    assert state.visit_counts == {"home": 1, "town": 1}


def test_staying_put_counts_nothing() -> None:
    state = _at("home", {"home": 1})
    assert apply_effects(state, {"move_to": "home"}).visit_counts == {"home": 1}
    assert apply_effects(state, {"set_flags": ["rested"]}).visit_counts == {"home": 1}
