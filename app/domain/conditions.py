from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.state import PlayerState


def evaluate_conditions(state: PlayerState, when: dict | None, repo) -> bool:
    """Evaluate all conditions in a 'when' block against current state.

    Null/empty/missing fields always pass (permissive default).
    """
    if not when:
        return True

    location = when.get("location")
    if location and location != state.current_place_id:
        return False

    zone = when.get("zone")
    if zone:
        place = repo.places_by_id.get(state.current_place_id, {})
        if place.get("zone_id") != zone:
            return False

    zone_not = when.get("zone_not")
    if zone_not:
        place = repo.places_by_id.get(state.current_place_id, {})
        if place.get("zone_id") == zone_not:
            return False

    for flag in when.get("flags_set") or []:
        if flag not in state.flags:
            return False

    for flag in when.get("flags_not_set") or []:
        if flag in state.flags:
            return False

    for item, min_qty in (when.get("inventory_min") or {}).items():
        if state.inventory.get(item, 0) < min_qty:
            return False

    for place_id, min_count in (when.get("visit_count_min") or {}).items():
        if state.visit_counts.get(place_id, 0) < min_count:
            return False

    for interaction, min_count in (when.get("seen_interactions_min") or {}).items():
        if state.seen_interactions.get(interaction, 0) < min_count:
            return False

    # time_of_day: skip in v1 (always passes)

    day_min = when.get("day_min")
    if day_min is not None and state.time_tick < day_min:
        return False

    day_max = when.get("day_max")
    if day_max is not None and state.time_tick > day_max:
        return False

    return True
