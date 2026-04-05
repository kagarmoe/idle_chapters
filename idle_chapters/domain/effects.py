from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from idle_chapters.domain.state import PlayerState


def apply_effects(state: PlayerState, effects: dict) -> PlayerState:
    """Apply effects to state, returning a new PlayerState. Never mutates input."""
    inventory = dict(state.inventory)
    flags = set(state.flags)
    place_id = state.current_place_id

    for item, qty in (effects.get("add_items") or {}).items():
        inventory[item] = inventory.get(item, 0) + qty

    for item, qty in (effects.get("remove_items") or {}).items():
        current = inventory.get(item, 0)
        if current < qty:
            raise ValueError(
                f"Cannot remove {qty} of '{item}': only {current} in inventory"
            )
        new_qty = current - qty
        if new_qty == 0:
            del inventory[item]
        else:
            inventory[item] = new_qty

    for flag in effects.get("set_flags") or []:
        flags.add(flag)

    for flag in effects.get("clear_flags") or []:
        flags.discard(flag)

    move_to = effects.get("move_to")
    if move_to is not None:
        place_id = move_to

    return replace(
        state,
        inventory=inventory,
        flags=flags,
        current_place_id=place_id,
    )
