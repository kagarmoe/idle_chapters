from dataclasses import replace

from idle_chapters.content.repo import ContentRepo
from idle_chapters.domain.daytime import TICKS_PER_PHASE
from idle_chapters.domain.engine import Engine
from idle_chapters.domain.state import PlayerState
from idle_chapters.domain.tea import pick_recipe


def _cottage(**overrides) -> PlayerState:
    return PlayerState(**{
        "session_id": "s", "current_place_id": "cottage_home", "inventory": {}, "flags": set(),
        "visit_counts": {"cottage_home": 1}, **overrides,
    })


def test_making_tea_brews_a_recipe_and_spends_nothing() -> None:
    repo, engine = ContentRepo(), Engine()
    entered = engine.step(_cottage(inventory={"honey": 1}), "enter", None, repo, seed=5)

    first = engine.step(entered.new_state, "choose option", "make_tea", repo, seed=7)
    again = engine.step(entered.new_state, "choose option", "make_tea", repo, seed=7)
    recipe = pick_recipe(first.new_state, repo, seed=7)

    assert first.journal_page["body"] == again.journal_page["body"]
    assert recipe["display_name"] in first.journal_page["body"]
    assert recipe["sensory_prompt"] in first.journal_page["body"]
    assert first.journal_page["ingredients"] == [i["ingredient_ref"] for i in recipe["ingredients"]]
    # Bountiful: honey is still there, and the kettle's gifts are added, never taken.
    assert first.new_state.inventory["honey"] == 1

    looked = engine.step(entered.new_state, "choose option", "look_around", repo, seed=7)
    assert not any(r["display_name"] in looked.journal_page["body"] for r in repo.tea_by_id.values())


def test_the_recipe_suits_the_hour_and_what_is_in_the_cupboard() -> None:
    repo = ContentRepo()
    holding = {"chamomile_flowers": 1, "black_tea": 1}
    for seed in range(6):
        morning = pick_recipe(_cottage(inventory=holding), repo, seed=seed)
        assert morning["recipe_id"] == "black_tea_simple"
        evening = pick_recipe(_cottage(inventory=holding, time_tick=4 * TICKS_PER_PHASE), repo, seed=seed)
        assert evening["recipe_id"] in {"chamomile_simple", "meadow_calm"}
    # Nothing fits the hour and nothing is held: any recipe will do.
    assert pick_recipe(replace(_cottage(), time_tick=TICKS_PER_PHASE), repo, seed=0)
