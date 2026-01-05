from types import SimpleNamespace


def test_engine_step_returns_journal_page() -> None:
    from app.domain.engine import Engine
    from app.domain.state import PlayerState

    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        storylets_by_place_id={},
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


def test_engine_determinism() -> None:
    from app.domain.engine import Engine
    from app.domain.state import PlayerState

    repo = SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        storylets_by_place_id={},
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
