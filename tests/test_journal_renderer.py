import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.content.schema_utils import load_validator


def _minimal_repo() -> SimpleNamespace:
    return SimpleNamespace(
        places_by_id={"cottage_home": {"place_id": "cottage_home", "zone_id": "cottage"}},
        journal_templates_by_entry_type={"tea": [{"template_id": "t1", "body": "{{prompt}}"}]},
        lexicon_by_key={},
    )


@pytest.mark.skip(reason="Journal renderer not yet implemented")
def test_render_journal_page_validates_schema(repo_root: Path) -> None:
    from app.domain.journal_renderer import render_journal_page

    schema_path = repo_root / "schemas" / "journal_page.schema.json"
    repo = _minimal_repo()

    # Action/scene context for rendering
    action = {
        "action_id": "action_1",
        "place_id": "cottage_home",
        "entry_type": "tea",
        "prompt": "A quiet cup.",
        "label": "Make tea",
        "result": "Steam rises gently.",
    }

    state = SimpleNamespace(
        session_id="session_1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
        time_tick=0,
    )

    page = render_journal_page(
        place_id="cottage_home",
        entry_type="tea",
        action=action,
        state=state,
        repo=repo,
        ingredient_picks=None,
    )

    assert "frontmatter" in page
    assert "body" in page
    validator = load_validator(schema_path)
    validator.validate(instance=page["frontmatter"])


@pytest.mark.skip(reason="Ingredient picker not yet implemented")
def test_ingredient_picker_locality_same_place() -> None:
    from app.domain.ingredient_picker import pick_ingredients

    repo = SimpleNamespace(
        places_by_id={
            "place_a": {"place_id": "place_a", "zone_id": "zone_1"},
            "place_b": {"place_id": "place_b", "zone_id": "zone_1"},
        },
        collectibles_by_id={
            "item_a": {"collectible_id": "item_a", "origin_scope": "place", "origin_ref": "place_a"},
            "item_b": {"collectible_id": "item_b", "origin_scope": "place", "origin_ref": "place_a"},
            "item_c": {"collectible_id": "item_c", "origin_scope": "place", "origin_ref": "place_b"},
        },
    )
    state = SimpleNamespace(current_place_id="place_a")

    picks = pick_ingredients(state=state, repo=repo, entry_type="tea")
    assert picks, "Expected ingredient picks"
    assert all(repo.collectibles_by_id[item_id]["origin_ref"] == "place_a" for item_id in picks)


@pytest.mark.skip(reason="Ingredient picker not yet implemented")
def test_ingredient_picker_locality_same_zone() -> None:
    from app.domain.ingredient_picker import pick_ingredients

    repo = SimpleNamespace(
        places_by_id={
            "place_a": {"place_id": "place_a", "zone_id": "zone_1"},
            "place_b": {"place_id": "place_b", "zone_id": "zone_1"},
            "place_c": {"place_id": "place_c", "zone_id": "zone_2"},
        },
        collectibles_by_id={
            "item_b": {"collectible_id": "item_b", "origin_scope": "place", "origin_ref": "place_b"},
            "item_c": {"collectible_id": "item_c", "origin_scope": "place", "origin_ref": "place_c"},
        },
    )
    state = SimpleNamespace(current_place_id="place_a")

    picks = pick_ingredients(state=state, repo=repo, entry_type="tea")
    assert picks, "Expected ingredient picks"
    assert all(
        repo.places_by_id[repo.collectibles_by_id[item_id]["origin_ref"]]["zone_id"] == "zone_1"
        for item_id in picks
    )


@pytest.mark.skip(reason="Ingredient picker not yet implemented")
def test_ingredient_picker_locality_any_place() -> None:
    from app.domain.ingredient_picker import pick_ingredients

    repo = SimpleNamespace(
        places_by_id={
            "place_a": {"place_id": "place_a", "zone_id": "zone_1"},
            "place_b": {"place_id": "place_b", "zone_id": "zone_2"},
        },
        collectibles_by_id={
            "item_b": {"collectible_id": "item_b", "origin_scope": "place", "origin_ref": "place_b"},
        },
    )
    state = SimpleNamespace(current_place_id="place_a")

    picks = pick_ingredients(state=state, repo=repo, entry_type="tea")
    assert picks, "Expected ingredient picks"
