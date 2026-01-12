import json
from pathlib import Path

import pytest
from app.content.schema_utils import load_validator


def _storylet_to_dict(storylet):
    if isinstance(storylet, dict):
        return storylet
    if hasattr(storylet, "model_dump"):
        return storylet.model_dump()
    if hasattr(storylet, "dict"):
        return storylet.dict()
    return storylet.__dict__


def _load_not_allowed_words(repo_root: Path) -> set[str]:
    lexicon_path = repo_root / "lexicons" / "not_allowed_lexicon.json"
    data = json.loads(lexicon_path.read_text())
    words = set()
    for entry in data.get("lexicon", []):
        words.update(word.lower() for word in entry.get("words", []))
    return words


def _storylet_text(storylet_dict: dict) -> str:
    parts = []
    for key in ("title", "prompt", "need_hint", "mood_hint"):
        value = storylet_dict.get(key)
        if isinstance(value, str):
            parts.append(value)
    for choice in storylet_dict.get("choices", []):
        label = choice.get("label")
        if isinstance(label, str):
            parts.append(label)
    return " ".join(parts).lower()


def test_generator_returns_three_choices() -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.storylet_generator import generate_storylet

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    storylet = generate_storylet(state=state, repo=repo, seed=123)
    data = _storylet_to_dict(storylet)
    assert len(data.get("choices", [])) == 3


def test_generator_determinism() -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.storylet_generator import generate_storylet

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    storylet_a = _storylet_to_dict(generate_storylet(state=state, repo=repo, seed=7))
    storylet_b = _storylet_to_dict(generate_storylet(state=state, repo=repo, seed=7))

    assert storylet_a.get("storylet_id") == storylet_b.get("storylet_id")
    labels_a = [choice.get("label") for choice in storylet_a.get("choices", [])]
    labels_b = [choice.get("label") for choice in storylet_b.get("choices", [])]
    assert labels_a == labels_b


@pytest.mark.skip(reason="storylet.schema.json removed; storylets replaced by scenes")
def test_generator_validates_against_schema(repo_root: Path) -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.storylet_generator import generate_storylet

    schema_path = repo_root / "schemas" / "storylet.schema.json"

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    storylet = _storylet_to_dict(generate_storylet(state=state, repo=repo, seed=99))
    validator = load_validator(schema_path)
    validator.validate(instance=storylet)


def test_generator_avoids_not_allowed_lexicon(repo_root: Path) -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.storylet_generator import generate_storylet

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    storylet = _storylet_to_dict(generate_storylet(state=state, repo=repo, seed=1))
    not_allowed = _load_not_allowed_words(repo_root)
    text = _storylet_text(storylet)

    for word in not_allowed:
        assert word not in text, f"Found disallowed word in storylet: {word}"


def test_selector_merges_authored_anchors() -> None:
    from app.domain.selector import merge_with_authored

    generated = [
        {"storylet_id": "generated_1", "place_id": "cottage_home", "choices": []},
        {"storylet_id": "generated_2", "place_id": "cottage_home", "choices": []},
    ]
    authored = [
        {"storylet_id": "authored_1", "place_id": "cottage_home", "choices": []},
    ]

    merged = merge_with_authored(generated, authored)
    ids = [storylet["storylet_id"] for storylet in merged]
    assert "authored_1" in ids


def test_generated_storylet_exists_for_all_places() -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.storylet_generator import generate_storylet

    repo = ContentRepo()

    for place_id in repo.places_by_id.keys():
        state = PlayerState(
            session_id="session_1",
            current_place_id=place_id,
            inventory={},
            flags=set(),
            time_tick=0,
        )
        storylet = generate_storylet(state=state, repo=repo, seed=10)
        assert storylet is not None
