from types import SimpleNamespace

from idle_chapters.content.repo import ContentRepo
from idle_chapters.domain.daytime import TICKS_PER_DAY, TICKS_PER_PHASE
from idle_chapters.domain.encounters import meet, present_npcs
from idle_chapters.domain.state import PlayerState


def _state(place: str, **overrides) -> PlayerState:
    return PlayerState(**{
        "session_id": "s", "current_place_id": place, "inventory": {}, "flags": set(),
        "visit_counts": {place: 1}, **overrides,
    })


def _interaction(interaction_id: str, kind: str = "spoken", **conditions) -> dict:
    return {
        "interaction_id": interaction_id,
        "npc_kind": "human",
        "text": {"kind": kind, "primary": f"{interaction_id}.", "secondary": None},
        "conditions": {"npc_id": "npc_ana", **conditions},
        "selection": {"weight": 1},
        "effects": {"set_flags": [f"heard_{interaction_id}"], "move_to": "elsewhere"},
    }


def _repo(*interactions: dict) -> SimpleNamespace:
    return SimpleNamespace(
        npcs_by_id={"npc_ana": {
            "npc_id": "npc_ana", "display_name": "Ana", "npc_kind": "human",
            "home_location_id": "porch", "spawn_rules": {"presence": "always"},
        }},
        interactions_by_id={i["interaction_id"]: i for i in interactions},
        places_by_id={"porch": {"place_id": "porch", "zone_id": "town"}},
    )


def test_a_meeting_is_told_counted_and_never_moves_you() -> None:
    state, interaction_id, line = meet(_state("porch"), _repo(_interaction("hello")), seed=1)

    assert (interaction_id, line) == ("hello", "“hello,” says Ana.")
    assert state.seen_interactions == {"hello": 1}
    assert "heard_hello" in state.flags
    assert state.current_place_id == "porch"


def test_time_of_day_and_cooldowns_decide_what_can_be_said() -> None:
    repo = _repo(
        _interaction("evening_only", time_of_day=["evening"]),
        _interaction("daily", once_per_day=True, cooldown_days=1),
    )
    morning = _state("porch")
    assert meet(morning, repo, seed=1)[1] == "daily"
    # Said once today: nothing else fits the morning, so nothing is said.
    assert meet(_state("porch", seen_interactions={"daily": 1}), repo, seed=1)[1] is None
    tomorrow = _state("porch", seen_interactions={"daily": 1}, time_tick=TICKS_PER_DAY)
    assert meet(tomorrow, repo, seed=1)[1] == "daily"
    evening = _state("porch", seen_interactions={"daily": 1}, time_tick=4 * TICKS_PER_PHASE)
    assert meet(evening, repo, seed=1)[1] == "evening_only"


def test_the_bakery_has_elin_and_moss_and_one_of_them_says_something() -> None:
    repo = ContentRepo()
    bakery = _state("town_bakery")

    assert {n["display_name"] for n in present_npcs(bakery, repo)} >= {"Elin the Baker", "Moss"}
    for seed in range(8):
        _, interaction_id, line = meet(bakery, repo, seed=seed)
        assert interaction_id and line
