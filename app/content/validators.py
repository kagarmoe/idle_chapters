from __future__ import annotations

from typing import Iterable


def _ensure_refs_exist(refs: Iterable[str], valid_ids: set[str], label: str) -> None:
    for ref in refs:
        if ref not in valid_ids:
            raise ValueError(f"Missing {label} reference: {ref}")


def _ingredient_ref_valid(ingredient_ref: str, collectible_ids: set[str]) -> bool:
    if ingredient_ref.startswith("any:"):
        return True
    return ingredient_ref in collectible_ids


def validate_cross_file_integrity(repo) -> None:
    place_ids = set(repo.places_by_id.keys())
    npc_ids = set(repo.npcs_by_id.keys())
    collectible_ids = set(repo.collectibles_by_id.keys())

    for npc in repo.npcs_by_id.values():
        home_location_id = npc.get("home_location_id")
        if home_location_id:
            _ensure_refs_exist([home_location_id], place_ids, "place_id")

    for collectible in repo.collectibles_by_id.values():
        origin_scope = collectible.get("origin_scope")
        origin_ref = collectible.get("origin_ref")
        if origin_scope == "place" and origin_ref:
            _ensure_refs_exist([origin_ref], place_ids, "place_id")

    for interaction in repo.interactions_by_id.values():
        conditions = interaction.get("conditions") or {}
        npc_id = conditions.get("npc_id")
        place_id = conditions.get("place_id")
        if npc_id:
            _ensure_refs_exist([npc_id], npc_ids, "npc_id")
        if place_id:
            _ensure_refs_exist([place_id], place_ids, "place_id")

    for recipe in repo.tea_by_id.values():
        for ingredient in recipe.get("ingredients", []):
            ingredient_ref = ingredient.get("ingredient_ref")
            if ingredient_ref and not _ingredient_ref_valid(ingredient_ref, collectible_ids):
                raise ValueError(f"Missing ingredient_ref: {ingredient_ref}")

    for spell in repo.spells_by_id.values():
        for ingredient in spell.get("ingredients", []):
            ingredient_ref = ingredient.get("ingredient_ref")
            if ingredient_ref and not _ingredient_ref_valid(ingredient_ref, collectible_ids):
                raise ValueError(f"Missing ingredient_ref: {ingredient_ref}")

    for entry in repo.lexicon_by_key.values():
        scope = entry.get("scope")
        if scope and scope != "Global":
            _ensure_refs_exist([scope], place_ids, "place_id")
