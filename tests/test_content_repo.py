from typing import Dict


def test_content_repo_builds_indices() -> None:
    from app.content.repo import ContentRepo

    repo = ContentRepo()
    expected_indices = [
        "places_by_id",
        "collectibles_by_id",
        "npcs_by_id",
        "interactions_by_id",
        "interactions_by_npc_kind",
        "interactions_by_place_id",
        "tea_by_id",
        "spells_by_id",
        "storylets_by_id",
        "storylets_by_place_id",
        "journal_templates_by_entry_type",
        "lexicon_by_key",
    ]

    for index_name in expected_indices:
        assert hasattr(repo, index_name), f"Missing index: {index_name}"
        assert isinstance(getattr(repo, index_name), dict), f"{index_name} must be a dict"


def test_content_repo_ids_are_strings() -> None:
    from app.content.repo import ContentRepo

    repo = ContentRepo()
    index_map: Dict[str, dict] = {
        "places_by_id": repo.places_by_id,
        "collectibles_by_id": repo.collectibles_by_id,
        "npcs_by_id": repo.npcs_by_id,
        "interactions_by_id": repo.interactions_by_id,
        "tea_by_id": repo.tea_by_id,
        "spells_by_id": repo.spells_by_id,
        "storylets_by_id": repo.storylets_by_id,
    }

    for index_name, index in index_map.items():
        for key in index.keys():
            assert isinstance(key, str), f"{index_name} key is not a string: {key}"
