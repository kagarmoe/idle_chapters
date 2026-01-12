import json
from pathlib import Path

import pytest
from app.content.schema_utils import load_validator


def _scene_to_dict(scene):
    if isinstance(scene, dict):
        return scene
    if hasattr(scene, "model_dump"):
        return scene.model_dump()
    if hasattr(scene, "dict"):
        return scene.dict()
    return scene.__dict__


def _load_not_allowed_words(repo_root: Path) -> set[str]:
    lexicon_path = repo_root / "lexicons" / "not_allowed_lexicon.json"
    data = json.loads(lexicon_path.read_text())
    words = set()
    for entry in data.get("lexicon", []):
        words.update(word.lower() for word in entry.get("words", []))
    return words


def _scene_text(scene_dict: dict) -> str:
    parts = []
    for key in ("title", "prompt", "need_hint", "mood_hint"):
        value = scene_dict.get(key)
        if isinstance(value, str):
            parts.append(value)
    for choice in scene_dict.get("choices", []):
        label = choice.get("label")
        if isinstance(label, str):
            parts.append(label)
    return " ".join(parts).lower()


def test_generator_returns_three_choices() -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.scene_generator import generate_scene

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    scene = generate_scene(state=state, repo=repo, seed=123)
    data = _scene_to_dict(scene)
    assert len(data.get("choices", [])) == 3


def test_generator_determinism() -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.scene_generator import generate_scene

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    scene_a = _scene_to_dict(generate_scene(state=state, repo=repo, seed=7))
    scene_b = _scene_to_dict(generate_scene(state=state, repo=repo, seed=7))

    assert scene_a.get("scene_id") == scene_b.get("scene_id")
    labels_a = [choice.get("label") for choice in scene_a.get("choices", [])]
    labels_b = [choice.get("label") for choice in scene_b.get("choices", [])]
    assert labels_a == labels_b


@pytest.mark.skip(reason="scene.schema.json removed; scenes replaced by scenes")
def test_generator_validates_against_schema(repo_root: Path) -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.scene_generator import generate_scene

    schema_path = repo_root / "schemas" / "scene.schema.json"

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    scene = _scene_to_dict(generate_scene(state=state, repo=repo, seed=99))
    validator = load_validator(schema_path)
    validator.validate(instance=scene)


def test_generator_avoids_not_allowed_lexicon(repo_root: Path) -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.scene_generator import generate_scene

    repo = ContentRepo()
    state = PlayerState(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    scene = _scene_to_dict(generate_scene(state=state, repo=repo, seed=1))
    not_allowed = _load_not_allowed_words(repo_root)
    text = _scene_text(scene)

    for word in not_allowed:
        assert word not in text, f"Found disallowed word in scene: {word}"


def test_selector_merges_authored_anchors() -> None:
    from app.domain.selector import merge_with_authored

    generated = [
        {"scene_id": "generated_1", "place_id": "cottage_home", "choices": []},
        {"scene_id": "generated_2", "place_id": "cottage_home", "choices": []},
    ]
    authored = [
        {"scene_id": "authored_1", "place_id": "cottage_home", "choices": []},
    ]

    merged = merge_with_authored(generated, authored)
    ids = [scene["scene_id"] for scene in merged]
    assert "authored_1" in ids


def test_generated_scene_exists_for_all_places() -> None:
    from app.content.repo import ContentRepo
    from app.domain.state import PlayerState
    from app.domain.scene_generator import generate_scene

    repo = ContentRepo()

    for place_id in repo.places_by_id.keys():
        state = PlayerState(
            session_id="session_1",
            current_place_id=place_id,
            inventory={},
            flags=set(),
            time_tick=0,
        )
        scene = generate_scene(state=state, repo=repo, seed=10)
        assert scene is not None
