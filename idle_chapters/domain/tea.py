"""The tea ritual: which recipe the kettle brews. Ingredients are noted, never spent."""

from __future__ import annotations

from idle_chapters.domain.daytime import time_of_day
from idle_chapters.domain.state import PlayerState

# Actions carry no recipe link in the schema, so the one tea-making action is named here.
TEA_ACTION = "make_tea"


def pick_recipe(state: PlayerState, repo, seed: int | None) -> dict | None:
    """A recipe that suits the hour and uses a base you hold, else the nearest fit, else any."""
    recipes = list(getattr(repo, "tea_by_id", {}).values())
    hour = time_of_day(state.time_tick)

    def suits(r: dict) -> bool:
        return hour in {t.lower() for t in r.get("allowed_times", [])}

    def held(r: dict) -> bool:
        return any(i.get("role") == "base" and state.inventory.get(i.get("ingredient_ref"), 0) > 0
                   for i in r.get("ingredients", []))

    for tier in ([r for r in recipes if suits(r) and held(r)], [r for r in recipes if suits(r)],
                 [r for r in recipes if held(r)], recipes):
        if tier:
            return tier[(seed or 0) % len(tier)]
    return None
