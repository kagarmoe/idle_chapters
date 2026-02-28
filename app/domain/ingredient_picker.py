"""Ingredient picker with locality-aware selection.

Locality cascade: same_place (strict) > same_zone > any_place.
No silent widening — the caller sees which policy was actually used.
"""

from __future__ import annotations

import hashlib
from typing import Any


def pick_ingredients(
    state,
    repo,
    entry_type: str,
    seed: int | None = None,
    max_picks: int = 3,
) -> list[str]:
    """Pick ingredients for a journal entry based on entry_type and locality.

    Returns a list of collectible_ids suitable for the given entry_type.
    """
    usable_filter = _usable_filter_for_entry_type(entry_type)
    candidates = _filter_candidates(repo, usable_filter, state.current_place_id)

    if not candidates:
        return []

    if seed is not None:
        candidates = _deterministic_shuffle(candidates, seed)

    return [c["collectible_id"] for c in candidates[:max_picks]]


def resolve_substitution_token(
    token: str,
    state,
    repo,
    seed: int | None = None,
) -> str | None:
    """Resolve an any: substitution token to a concrete collectible_id.

    Uses the place_policy from the substitution rule to enforce locality.
    Falls back to the rule's fallback value if no match found.
    """
    rule = repo.ingredient_substitutions_by_token.get(token)
    if not rule:
        return None

    constraints = rule.get("constraints", {})
    place_policy = constraints.get("place_policy", "any_place")
    required_tags = set(constraints.get("tags", []))
    required_category = constraints.get("category")
    max_results = constraints.get("max_results", 10)

    candidates = _match_collectibles(
        repo,
        required_tags=required_tags,
        required_category=required_category,
        place_policy=place_policy,
        current_place_id=state.current_place_id,
    )

    if not candidates:
        return rule.get("fallback")

    candidates = candidates[:max_results]

    if seed is not None:
        candidates = _deterministic_shuffle(candidates, seed)

    return candidates[0]["collectible_id"]


def _usable_filter_for_entry_type(entry_type: str) -> str | None:
    """Map entry_type to the usable_in tag for filtering collectibles."""
    mapping = {
        "tea": "tea",
        "spell": "spell",
    }
    return mapping.get(entry_type)


def _filter_candidates(
    repo,
    usable_filter: str | None,
    current_place_id: str,
) -> list[dict[str, Any]]:
    """Filter collectibles by usable_in and sort by locality.

    Locality cascade: same_place > same_zone > any_place.
    """
    place = repo.places_by_id.get(current_place_id, {})
    current_zone_id = place.get("zone_id")

    same_place: list[dict[str, Any]] = []
    same_zone: list[dict[str, Any]] = []
    any_place: list[dict[str, Any]] = []

    for item in repo.collectibles_by_id.values():
        if usable_filter and usable_filter not in item.get("usable_in", []):
            continue

        origin_scope = item.get("origin_scope", "global")
        origin_ref = item.get("origin_ref")

        if origin_scope == "global" or origin_scope == "starting":
            any_place.append(item)
        elif origin_ref == current_place_id:
            same_place.append(item)
        elif current_zone_id and origin_ref == current_zone_id:
            same_zone.append(item)
        else:
            any_place.append(item)

    return same_place + same_zone + any_place


def _match_collectibles(
    repo,
    required_tags: set[str],
    required_category: str | None,
    place_policy: str,
    current_place_id: str,
) -> list[dict[str, Any]]:
    """Match collectibles against substitution constraints with locality enforcement."""
    place = repo.places_by_id.get(current_place_id, {})
    current_zone_id = place.get("zone_id")

    matches: list[dict[str, Any]] = []

    for item in repo.collectibles_by_id.values():
        item_tags = set(item.get("tags", []))
        if required_tags and not required_tags.issubset(item_tags):
            continue

        if required_category:
            item_type = item.get("item_type", "")
            botanical_kind = item.get("botanical_kind")
            if item_type != required_category and botanical_kind != required_category:
                continue

        if not _passes_locality(item, place_policy, current_place_id, current_zone_id):
            continue

        matches.append(item)

    return matches


def _passes_locality(
    item: dict[str, Any],
    place_policy: str,
    current_place_id: str,
    current_zone_id: str | None,
) -> bool:
    """Check if a collectible passes the given place_policy locality filter."""
    if place_policy == "any_place":
        return True

    origin_scope = item.get("origin_scope", "global")
    origin_ref = item.get("origin_ref")

    if place_policy == "same_place":
        return origin_ref == current_place_id

    if place_policy == "same_zone":
        if origin_ref == current_place_id:
            return True
        return bool(current_zone_id and origin_ref == current_zone_id)

    return True


def _deterministic_shuffle(
    items: list[dict[str, Any]], seed: int
) -> list[dict[str, Any]]:
    """Deterministic ordering based on seed + item id."""
    def sort_key(item: dict[str, Any]) -> str:
        item_id = item.get("collectible_id", "")
        return hashlib.md5(f"{seed}:{item_id}".encode()).hexdigest()

    return sorted(items, key=sort_key)
