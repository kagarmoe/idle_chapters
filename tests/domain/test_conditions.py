from types import SimpleNamespace

from idle_chapters.domain.conditions import evaluate_conditions
from idle_chapters.domain.state import PlayerState


def _make_state(**overrides) -> PlayerState:
    defaults = dict(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )
    defaults.update(overrides)
    return PlayerState(**defaults)


def _make_repo(**overrides) -> SimpleNamespace:
    defaults = dict(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_none_when_passes() -> None:
    assert evaluate_conditions(_make_state(), None, _make_repo()) is True


def test_empty_when_passes() -> None:
    assert evaluate_conditions(_make_state(), {}, _make_repo()) is True


def test_location_match() -> None:
    when = {"location": "cottage_home"}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is True


def test_location_mismatch() -> None:
    when = {"location": "forest_clearing"}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is False


def test_zone_match() -> None:
    when = {"zone": "cottage"}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is True


def test_zone_mismatch() -> None:
    when = {"zone": "forest"}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is False


def test_zone_not_passes() -> None:
    when = {"zone_not": "forest"}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is True


def test_zone_not_fails() -> None:
    when = {"zone_not": "cottage"}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is False


def test_flags_set_passes() -> None:
    state = _make_state(flags={"found_key"})
    when = {"flags_set": ["found_key"]}
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_flags_set_fails() -> None:
    when = {"flags_set": ["found_key"]}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is False


def test_flags_not_set_passes() -> None:
    when = {"flags_not_set": ["found_key"]}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is True


def test_flags_not_set_fails() -> None:
    state = _make_state(flags={"found_key"})
    when = {"flags_not_set": ["found_key"]}
    assert evaluate_conditions(state, when, _make_repo()) is False


def test_inventory_min_passes() -> None:
    state = _make_state(inventory={"key": 3})
    when = {"inventory_min": {"key": 2}}
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_inventory_min_fails() -> None:
    state = _make_state(inventory={"key": 1})
    when = {"inventory_min": {"key": 2}}
    assert evaluate_conditions(state, when, _make_repo()) is False


def test_visit_count_min_passes() -> None:
    state = _make_state(visit_counts={"cottage_home": 5})
    when = {"visit_count_min": {"cottage_home": 3}}
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_visit_count_min_fails() -> None:
    when = {"visit_count_min": {"cottage_home": 3}}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is False


def test_seen_interactions_min_passes() -> None:
    state = _make_state(seen_interactions={"make_tea": 2})
    when = {"seen_interactions_min": {"make_tea": 1}}
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_seen_interactions_min_fails() -> None:
    when = {"seen_interactions_min": {"make_tea": 1}}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is False


def test_day_min_passes() -> None:
    state = _make_state(time_tick=5)
    when = {"day_min": 3}
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_day_min_fails() -> None:
    state = _make_state(time_tick=1)
    when = {"day_min": 3}
    assert evaluate_conditions(state, when, _make_repo()) is False


def test_day_max_passes() -> None:
    state = _make_state(time_tick=2)
    when = {"day_max": 5}
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_day_max_fails() -> None:
    state = _make_state(time_tick=10)
    when = {"day_max": 5}
    assert evaluate_conditions(state, when, _make_repo()) is False


def test_combined_conditions() -> None:
    state = _make_state(
        flags={"made_tea"},
        inventory={"key": 1},
        time_tick=3,
    )
    when = {
        "location": "cottage_home",
        "flags_set": ["made_tea"],
        "inventory_min": {"key": 1},
        "day_min": 2,
        "day_max": 5,
    }
    assert evaluate_conditions(state, when, _make_repo()) is True


def test_time_of_day_always_passes() -> None:
    when = {"time_of_day": ["morning", "afternoon"]}
    assert evaluate_conditions(_make_state(), when, _make_repo()) is True
