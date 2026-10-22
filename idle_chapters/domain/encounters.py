"""Who is here, and the one small thing someone says or does when you arrive (interactions_design.md)."""

from __future__ import annotations

import random
from dataclasses import replace

from idle_chapters.domain.daytime import day, time_of_day
from idle_chapters.domain.effects import apply_effects
from idle_chapters.domain.state import PlayerState


def present_npcs(state: PlayerState, repo) -> list[dict]:
    """NPCs at home here. Scheduled and rotating ones come and go, decided once per visit."""
    place = state.current_place_id
    visit = state.visit_counts.get(place, 0)
    return [
        npc for npc in getattr(repo, "npcs_by_id", {}).values()
        if npc.get("home_location_id") == place
        and ((npc.get("spawn_rules") or {}).get("presence", "always") == "always"
             or random.Random(f"{state.session_id}:{npc['npc_id']}:{visit}").random() < 0.5)
    ]


def meet(state: PlayerState, repo, seed: int | None) -> tuple[PlayerState, str | None, str | None]:
    """Pick one interaction with someone present; returns the new state, its id and its line."""
    npcs = present_npcs(state, repo)
    interactions = getattr(repo, "interactions_by_id", {}).values() if npcs else []
    options = [(i, s) for i in interactions if (s := _speakers(i, state, repo, npcs))]
    if not options:
        return state, None, None

    rng = random.Random(f"meet:{seed}")
    # Familiar things come round less often; nothing is ever used up.
    weights = [
        (i.get("selection") or {}).get("weight", 1) / (1 + state.seen_interactions.get(i["interaction_id"], 0))
        for i, _ in options
    ]
    interaction, speakers = rng.choices(options, weights)[0]
    speaker = rng.choice(speakers)

    # An NPC never moves the player.
    effects = {k: v for k, v in (interaction.get("effects") or {}).items() if k != "move_to" and v}
    seen = dict(state.seen_interactions)
    seen[interaction["interaction_id"]] = seen.get(interaction["interaction_id"], 0) + 1
    new_state = replace(apply_effects(state, effects), seen_interactions=seen)
    return new_state, interaction["interaction_id"], _line(interaction, speaker)


def _speakers(interaction: dict, state: PlayerState, repo, npcs: list[dict]) -> list[dict]:
    c = interaction.get("conditions") or {}
    place = repo.places_by_id.get(state.current_place_id, {})
    seen = state.seen_interactions
    if c.get("place_id") not in (None, state.current_place_id):
        return []
    if c.get("zone_id") not in (None, place.get("zone_id")):
        return []
    if c.get("time_of_day") and time_of_day(state.time_tick) not in c["time_of_day"]:
        return []
    if c.get("weather") or c.get("season"):
        return []  # weather and seasons are not modelled yet
    required = c.get("requires_seen") or []
    if any(not seen.get(r) for r in ([required] if isinstance(required, str) else required)):
        return []
    # shortcut: a cooldown is a budget (seen at most once per cooldown period since day 0), not a per-day timestamp; store last-seen days if it needs to be exact.
    cooldown = max(c.get("cooldown_days") or 0, 1 if c.get("once_per_day") else 0)
    if cooldown and seen.get(interaction["interaction_id"], 0) > day(state.time_tick) // cooldown:
        return []
    if c.get("npc_id"):
        return [n for n in npcs if n["npc_id"] == c["npc_id"]]
    return [n for n in npcs if n.get("npc_kind") == interaction.get("npc_kind")]


def _line(interaction: dict, speaker: dict) -> str:
    text = interaction.get("text") or {}
    name = speaker.get("display_name", "Someone")
    primary = text.get("primary", "")
    if text.get("kind") == "spoken":
        said = primary[:-1] + "," if primary.endswith(".") else primary
        line = f"“{said}” says {name}."
    else:
        line = name + primary[len("The animal"):] if primary.startswith("The animal") else primary
    return f"{line} {text['secondary']}" if text.get("secondary") else line
