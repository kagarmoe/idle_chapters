import pytest


def test_apply_effects_updates_state() -> None:
    from app.domain.effects import apply_effects
    from app.domain.state import PlayerState

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
    from app.domain.effects import apply_effects
    from app.domain.state import PlayerState

    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={"item_1": 0},
        flags=set(),
        time_tick=0,
    )

    effects = {"remove_items": {"item_1": 1}}

    with pytest.raises(ValueError):
        apply_effects(state, effects)
