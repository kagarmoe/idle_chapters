from types import SimpleNamespace

from idle_chapters.domain.engine import Engine
from idle_chapters.domain.state import PlayerState


def test_engine_step_returns_journal_page() -> None:
    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={},
        actions_by_id={},
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}]},
        journal_templates_by_id={"t1": {"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )

    engine = Engine()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    result = engine.step(state=state, command="enter", choice_id=None, repo=repo, seed=123)

    assert result.journal_page is not None
    assert len(result.choices) == 3


def test_engine_determinism() -> None:
    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={},
        actions_by_id={},
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}]},
        journal_templates_by_id={"t1": {"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )

    engine = Engine()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    result_a = engine.step(state=state, command="enter", choice_id=None, repo=repo, seed=5)
    result_b = engine.step(state=state, command="enter", choice_id=None, repo=repo, seed=5)

    assert result_a.journal_page == result_b.journal_page
    assert result_a.choices == result_b.choices


def test_engine_apply_effects_changes_state() -> None:
    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={
            "cottage_home": [
                {
                    "scene_id": "s1",
                    "nodes": [
                        {
                            "node_id": "n1",
                            "action_ref": "a1",
                            "choices": [],
                        }
                    ],
                }
            ]
        },
        actions_by_id={
            "a1": {
                "action_id": "a1",
                "label": "Find key",
                "effects": {"add_items": {"key": 1}, "set_flags": ["found_key"]},
            }
        },
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}]},
        journal_templates_by_id={"t1": {"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )

    engine = Engine()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    result = engine.step(state=state, command="choose option", choice_id="a1", repo=repo, seed=123)

    assert "key" in result.new_state.inventory
    assert "found_key" in result.new_state.flags
    assert result.journal_page is not None


def test_engine_journal_page_reflects_step() -> None:
    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={
            "cottage_home": [
                {
                    "scene_id": "s1",
                    "nodes": [
                        {
                            "node_id": "n1",
                            "action_ref": "a1",
                            "choices": [],
                        }
                    ],
                }
            ]
        },
        actions_by_id={
            "a1": {
                "action_id": "a1",
                "label": "Find key",
                "effects": {"add_items": {"key": 1}, "set_flags": ["found_key"]},
            }
        },
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}]},
        journal_templates_by_id={"t1": {"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )

    engine = Engine()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    result = engine.step(state=state, command="choose option", choice_id="a1", repo=repo, seed=123)

    assert result.journal_page is not None


def _travel_repo() -> SimpleNamespace:
    def scene(place: str, entry: str, choices: list[str], extra: list[dict]) -> dict:
        return {
            "scene_id": f"s_{place}",
            "place_id": place,
            "entry_node": entry,
            "nodes": [{"node_id": entry, "action_ref": "rest", "choices": choices}, *extra],
        }

    template = {"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}
    return SimpleNamespace(
        places_by_id={
            "home": {"place_id": "home", "zone_id": "cottage"},
            "town": {"place_id": "town", "zone_id": "town"},
        },
        scenes_by_place_id={
            "home": [scene("home", "n_home", ["n_go_town"], [
                {"node_id": "n_go_town", "action_ref": "go_town", "choices": []},
            ])],
            "town": [scene("town", "n_town", ["n_go_home", "n_regular"], [
                {"node_id": "n_go_home", "action_ref": "go_home", "choices": []},
                {"node_id": "n_regular", "action_ref": "regular", "choices": []},
            ])],
        },
        actions_by_id={
            "rest": {"action_id": "rest", "label": "Rest", "effects": {}},
            "go_town": {"action_id": "go_town", "label": "Walk to town", "effects": {"move_to": "town"}},
            "go_home": {"action_id": "go_home", "label": "Walk home", "effects": {"move_to": "home"}},
            "regular": {"action_id": "regular", "label": "Wave to the baker", "when": {"visit_count_min": {"town": 2}}},
        },
        journal_templates_by_entry_type={"tea": [template]},
        journal_templates_by_id={"t1": template},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )


def test_visit_gated_action_appears_from_the_second_arrival() -> None:
    repo, engine = _travel_repo(), Engine()
    state = PlayerState(session_id="s", current_place_id="home", inventory={}, flags=set(), time_tick=0, visit_counts={"home": 1})

    def arrive_in_town(state):
        state = engine.step(state, "enter", None, repo, seed=1).new_state
        state = engine.step(state, "choose option", "go_town", repo, seed=1).new_state
        return engine.step(state, "enter", None, repo, seed=1)

    first = arrive_in_town(state)
    assert first.new_state.visit_counts == {"home": 1, "town": 1}
    assert "regular" not in {c["action_id"] for c in first.choices}

    back_home = engine.step(first.new_state, "choose option", "go_home", repo, seed=1).new_state
    second = arrive_in_town(back_home)
    assert second.new_state.visit_counts == {"home": 2, "town": 2}
    assert "regular" in {c["action_id"] for c in second.choices}


def _paths_repo() -> SimpleNamespace:
    template = {"template_id": "t1", "entry_type": "tea", "prompt": "What softened today?", "structure": ["A moment passed quietly."], "tags": []}
    return SimpleNamespace(
        places_by_id={
            "home": {"place_id": "home", "zone_id": "cottage"},
            "town": {"place_id": "town", "zone_id": "town"},
        },
        scenes_by_place_id={
            "home": [{
                "scene_id": "s_home",
                "place_id": "home",
                "entry_node": "n_rest",
                "nodes": [
                    {"node_id": "n_rest", "action_ref": "rest", "choices": ["n_tea"]},
                    {"node_id": "n_tea", "action_ref": "tea", "choices": []},
                ],
            }],
        },
        actions_by_id={
            "rest": {"action_id": "rest", "label": "Rest", "effects": {}},
            "tea": {"action_id": "tea", "label": "Make tea", "effects": {}},
            "go_town": {"action_id": "go_town", "label": "Walk to town", "when": {"location": "home"}, "effects": {"move_to": "town"}, "result": "The lane is easy."},
            "go_home": {"action_id": "go_home", "label": "Wander home", "when": {"zone_not": "cottage"}, "effects": {"move_to": "home"}, "result": "You take the long way."},
            "locked": {"action_id": "locked", "label": "Locked", "when": {"flags_set": ["never"]}, "effects": {"move_to": "town"}},
        },
        journal_templates_by_entry_type={"tea": [template]},
        journal_templates_by_id={"t1": template},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )


def _ids(result) -> list[str]:
    return [c.get("action_id") or c.get("choice_id") for c in result.choices]


def test_paths_follow_the_scene_choices_once_each() -> None:
    repo, engine = _paths_repo(), Engine()
    home = PlayerState(session_id="s", current_place_id="home", inventory={}, flags=set(), time_tick=0, visit_counts={"home": 1})

    entered = engine.step(home, "enter", None, repo, seed=1)
    assert _ids(entered) == ["tea", "go_town"]


def test_taking_a_path_tells_the_walk_and_arrives() -> None:
    repo, engine = _paths_repo(), Engine()
    home = PlayerState(session_id="s", current_place_id="home", inventory={}, flags=set(), time_tick=0, visit_counts={"home": 1})

    in_town = engine.step(home, "choose option", "go_town", repo, seed=1)
    assert in_town.new_state.current_place_id == "town"
    assert in_town.new_state.visit_counts == {"home": 1, "town": 1}
    assert "The lane is easy." in in_town.journal_page["body"]
    assert "go_home" in _ids(in_town)
    assert in_town.debug["choice_id"] == "go_town"
    assert in_town.debug["selected_scene_id"] == in_town.new_state.current_scene_id

    back = engine.step(in_town.new_state, "choose option", "go_home", repo, seed=2)
    assert back.new_state.current_place_id == "home"
    assert back.new_state.current_scene_id == "s_home"
    assert _ids(back) == ["tea", "go_town"]


def test_a_path_whose_when_fails_is_refused() -> None:
    import pytest

    from idle_chapters.domain.errors import ActionNotEligible

    repo, engine = _paths_repo(), Engine()
    home = PlayerState(session_id="s", current_place_id="home", inventory={}, flags=set(), time_tick=0)

    with pytest.raises(ActionNotEligible):
        engine.step(home, "choose option", "locked", repo, seed=1)
