from types import SimpleNamespace

import pytest


def _minimal_repo() -> SimpleNamespace:
    return SimpleNamespace(
        places_by_id={"place_1": {"place_id": "place_1"}},
        npcs_by_id={"npc_1": {"npc_id": "npc_1", "home_place_id": "place_1"}},
        collectibles_by_id={"item_1": {"collectible_id": "item_1", "origin_scope": "place", "origin_ref": "place_1"}},
        interactions_by_id={"interaction_1": {"interaction_id": "interaction_1", "place_id": "place_1", "npc_id": "npc_1"}},
        tea_by_id={"tea_1": {"tea_id": "tea_1", "ingredients": ["item_1"]}},
        spells_by_id={},
        lexicon_by_key={},
    )


def test_validate_cross_file_integrity_passes() -> None:
    from app.content.validators import validate_cross_file_integrity

    repo = _minimal_repo()
    validate_cross_file_integrity(repo)


def test_validate_cross_file_integrity_missing_place() -> None:
    from app.content.validators import validate_cross_file_integrity

    repo = _minimal_repo()
    repo.npcs_by_id["npc_1"]["home_place_id"] = "missing_place"

    with pytest.raises(ValueError, match="missing_place"):
        validate_cross_file_integrity(repo)
