import pytest
from types import SimpleNamespace

# Engine is not yet implemented - all tests are skipped
# See V1_PLAYABLE_PLAN.md Milestone 4 for engine implementation plan


@pytest.mark.skip(reason="Engine not yet implemented")
def test_engine_step_returns_journal_page() -> None:
    from app.domain.engine import Engine
    from app.domain.state import PlayerState

    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={},
        actions_by_id={},
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "body": "{{prompt}}"}]},
        lexicon_by_key={},
        collectibles_by_id={},
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


@pytest.mark.skip(reason="Engine not yet implemented")
def test_engine_determinism() -> None:
    from app.domain.engine import Engine
    from app.domain.state import PlayerState

    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        scenes_by_place_id={},
        actions_by_id={},
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "body": "{{prompt}}"}]},
        lexicon_by_key={},
        collectibles_by_id={},
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


@pytest.mark.skip(reason="Engine not yet implemented")
def test_engine_apply_effects_changes_state() -> None:
    from app.domain.engine import Engine
    from app.domain.state import PlayerState

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
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "body": "{{prompt}}"}]},
        lexicon_by_key={},
        collectibles_by_id={},
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


@pytest.mark.skip(reason="Engine not yet implemented")
def test_engine_journal_page_reflects_step() -> None:
    from app.domain.engine import Engine
    from app.domain.state import PlayerState

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
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "body": "{{prompt}}"}]},
        lexicon_by_key={},
        collectibles_by_id={},
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
