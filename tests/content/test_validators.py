from types import SimpleNamespace

import pytest


def _minimal_repo() -> SimpleNamespace:
    return SimpleNamespace(
        places_by_id={"place_1": {"place_id": "place_1"}},
        npcs_by_id={"npc_1": {"npc_id": "npc_1", "home_location_id": "place_1"}},
        collectibles_by_id={"item_1": {"collectible_id": "item_1", "origin_scope": "place", "origin_ref": "place_1"}},
        interactions_by_id={"interaction_1": {"interaction_id": "interaction_1", "conditions": {"place_id": "place_1", "npc_id": "npc_1"}}},
        tea_by_id={"tea_1": {"tea_id": "tea_1", "ingredients": [{"ingredient_ref": "item_1", "role": "base", "amount_hint": "1 tsp"}]}},
        spells_by_id={},
        lexicon_by_key={},
        actions_by_id={"go": {"action_id": "go", "when": {"location": "place_1"}, "effects": {"move_to": "place_1"}}},
    )


def test_validate_cross_file_integrity_passes() -> None:
    from idle_chapters.content.validators import validate_cross_file_integrity

    repo = _minimal_repo()
    validate_cross_file_integrity(repo)


def test_shipped_assets_pass_cross_file_integrity() -> None:
    from idle_chapters.content.repo import ContentRepo
    from idle_chapters.content.validators import validate_cross_file_integrity

    validate_cross_file_integrity(ContentRepo())


def test_validate_cross_file_integrity_missing_place() -> None:
    from idle_chapters.content.validators import validate_cross_file_integrity

    repo = _minimal_repo()
    repo.npcs_by_id["npc_1"]["home_location_id"] = "missing_place"

    with pytest.raises(ValueError, match="missing_place"):
        validate_cross_file_integrity(repo)


@pytest.mark.parametrize("field", ["move_to", "location"])
def test_a_path_to_an_unknown_place_fails(field) -> None:
    from idle_chapters.content.validators import validate_cross_file_integrity

    repo = _minimal_repo()
    action = repo.actions_by_id["go"]
    (action["effects"] if field == "move_to" else action["when"])[field] = "forrest"

    with pytest.raises(ValueError, match="forrest"):
        validate_cross_file_integrity(repo)
