"""Tests for journal renderer and ingredient picker (M3)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from app.domain.ingredient_picker import (
    pick_ingredients,
    resolve_substitution_token,
)
from app.domain.journal_renderer import render_journal_page


REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_repo(**overrides) -> SimpleNamespace:
    """Build a minimal mock repo for testing."""
    defaults = dict(
        places_by_id={
            "cottage_home": {
                "place_id": "cottage_home",
                "zone_id": "cottage",
                "display_name": "Cottage",
                "mood": "Safe",
                "is_threshold": False,
                "profile": {
                    "player_need_satisfied": "Permission to rest and recover",
                },
            },
        },
        zones_by_id={
            "cottage": {"zone_id": "cottage", "display_name": "Cottage"},
        },
        journal_templates_by_entry_type={
            "tea": [
                {
                    "template_id": "tea_reflection_v1",
                    "entry_type": "tea",
                    "prompt": "What softened today?",
                    "structure": [
                        "A small sensory detail from the place.",
                        "Why I chose these ingredients.",
                        "What I want to carry forward (one sentence).",
                    ],
                    "tags": [],
                }
            ],
        },
        journal_templates_by_id={
            "tea_reflection_v1": {
                "template_id": "tea_reflection_v1",
                "entry_type": "tea",
                "prompt": "What softened today?",
                "structure": [
                    "A small sensory detail from the place.",
                    "Why I chose these ingredients.",
                    "What I want to carry forward (one sentence).",
                ],
                "tags": [],
            },
        },
        collectibles_by_id={
            "chamomile_flowers": {
                "collectible_id": "chamomile_flowers",
                "display_name": "Chamomile Flowers",
                "item_type": "Botanical",
                "tags": ["calming", "element_earth"],
                "origin_scope": "global",
                "origin_ref": None,
                "usable_in": ["tea", "spell"],
            },
            "lavender": {
                "collectible_id": "lavender",
                "display_name": "Lavender",
                "item_type": "Botanical",
                "tags": ["calming", "element_earth"],
                "origin_scope": "zone",
                "origin_ref": "cottage",
                "usable_in": ["tea", "spell"],
            },
        },
        ingredient_substitutions_by_token={},
        lexicon_by_key={},
        actions_by_id={},
        scenes_by_place_id={},
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_state(place_id: str = "cottage_home") -> SimpleNamespace:
    return SimpleNamespace(
        session_id="test_session",
        current_place_id=place_id,
        inventory={},
        flags=set(),
        time_tick=0,
    )


# --- Journal Renderer Tests ---


def test_render_journal_page_returns_required_fields():
    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "Steam rises gently."}

    page = render_journal_page(
        place_id="cottage_home",
        entry_type="tea",
        action=action,
        state=state,
        repo=repo,
        seed=42,
    )

    required_fields = ["page_id", "date", "place_id", "entry_type", "mood", "need", "ingredients", "prompt", "body"]
    for field in required_fields:
        assert field in page, f"Missing required field: {field}"


def test_render_journal_page_validates_against_schema():
    schema_path = REPO_ROOT / "schemas" / "journal_page.schema.json"
    if not schema_path.exists():
        pytest.skip("journal_page.schema.json not found")

    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "Steam rises gently."}

    page = render_journal_page(
        place_id="cottage_home",
        entry_type="tea",
        action=action,
        state=state,
        repo=repo,
        seed=42,
    )

    schema_data = json.loads(schema_path.read_text())
    inner_schema = schema_data["properties"]["journal_page"]

    resolver = jsonschema.RefResolver(
        base_uri=f"file://{schema_path.parent}/",
        referrer=schema_data,
    )
    jsonschema.validate(instance=page, schema=inner_schema, resolver=resolver)


def test_render_journal_page_determinism():
    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "Steam rises gently."}

    page_a = render_journal_page(
        place_id="cottage_home", entry_type="tea", action=action,
        state=state, repo=repo, seed=42,
    )
    page_b = render_journal_page(
        place_id="cottage_home", entry_type="tea", action=action,
        state=state, repo=repo, seed=42,
    )

    assert page_a["page_id"] == page_b["page_id"]
    assert page_a["body"] == page_b["body"]
    assert page_a["mood"] == page_b["mood"]


def test_render_journal_page_mood_from_place():
    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "test"}

    page = render_journal_page(
        place_id="cottage_home", entry_type="tea", action=action,
        state=state, repo=repo, seed=1,
    )

    assert page["mood"] == "Safe"


def test_render_journal_page_need_from_place_profile():
    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "test"}

    page = render_journal_page(
        place_id="cottage_home", entry_type="tea", action=action,
        state=state, repo=repo, seed=1,
    )

    assert page["need"] == "Permission to rest and recover"


def test_render_journal_page_body_nonempty():
    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "Steam rises."}

    page = render_journal_page(
        place_id="cottage_home", entry_type="tea", action=action,
        state=state, repo=repo, seed=1,
    )

    assert page["body"]
    assert len(page["body"]) > 0


def test_render_journal_page_with_ingredients():
    repo = _make_repo()
    state = _make_state()
    action = {"action_id": "a1", "result": "test"}

    page = render_journal_page(
        place_id="cottage_home", entry_type="tea", action=action,
        state=state, repo=repo,
        ingredient_picks=["chamomile_flowers", "lavender"],
        seed=1,
    )

    assert page["ingredients"] == ["chamomile_flowers", "lavender"]
    assert "Chamomile Flowers" in page["body"] or "Lavender" in page["body"]


def test_render_journal_page_fallback_template():
    """Renderer should produce a page even for entry_types with no template."""
    repo = _make_repo(journal_templates_by_entry_type={})
    state = _make_state()
    action = {"action_id": "a1", "result": "test"}

    page = render_journal_page(
        place_id="cottage_home", entry_type="dream_fragment", action=action,
        state=state, repo=repo, seed=1,
    )

    assert page["entry_type"] == "dream_fragment"
    assert page["body"]


# --- Ingredient Picker Tests ---


def test_pick_ingredients_returns_list():
    repo = _make_repo()
    state = _make_state()

    picks = pick_ingredients(state, repo, "tea", seed=42)

    assert isinstance(picks, list)
    assert len(picks) <= 3


def test_pick_ingredients_locality_same_zone_preferred():
    """Items from the same zone should appear before global items."""
    repo = _make_repo(
        collectibles_by_id={
            "local_herb": {
                "collectible_id": "local_herb",
                "display_name": "Local Herb",
                "item_type": "Botanical",
                "tags": ["calming"],
                "origin_scope": "zone",
                "origin_ref": "cottage",
                "usable_in": ["tea"],
            },
            "global_herb": {
                "collectible_id": "global_herb",
                "display_name": "Global Herb",
                "item_type": "Botanical",
                "tags": ["calming"],
                "origin_scope": "global",
                "origin_ref": None,
                "usable_in": ["tea"],
            },
        },
    )
    state = _make_state()

    # Without seed, locality ordering puts same_zone before any_place
    picks = pick_ingredients(state, repo, "tea", max_picks=2)

    assert len(picks) == 2
    assert picks[0] == "local_herb"


def test_pick_ingredients_filters_by_usable_in():
    """Tea picks should only include items usable in tea."""
    repo = _make_repo(
        collectibles_by_id={
            "tea_herb": {
                "collectible_id": "tea_herb",
                "item_type": "Botanical",
                "tags": [],
                "origin_scope": "global",
                "origin_ref": None,
                "usable_in": ["tea"],
            },
            "spell_only": {
                "collectible_id": "spell_only",
                "item_type": "Crystal",
                "tags": [],
                "origin_scope": "global",
                "origin_ref": None,
                "usable_in": ["spell"],
            },
        },
    )
    state = _make_state()

    picks = pick_ingredients(state, repo, "tea")

    assert "tea_herb" in picks
    assert "spell_only" not in picks


def test_pick_ingredients_determinism():
    repo = _make_repo()
    state = _make_state()

    picks_a = pick_ingredients(state, repo, "tea", seed=99)
    picks_b = pick_ingredients(state, repo, "tea", seed=99)

    assert picks_a == picks_b


def test_pick_ingredients_empty_for_no_matches():
    repo = _make_repo(collectibles_by_id={})
    state = _make_state()

    picks = pick_ingredients(state, repo, "tea")
    assert picks == []


def test_pick_ingredients_field_note_no_usable_filter():
    """field_note entry_type should allow any collectible (no usable_in filter)."""
    repo = _make_repo(
        collectibles_by_id={
            "crystal": {
                "collectible_id": "crystal",
                "item_type": "Crystal",
                "tags": [],
                "origin_scope": "global",
                "origin_ref": None,
                "usable_in": ["spell"],
            },
        },
    )
    state = _make_state()

    picks = pick_ingredients(state, repo, "field_note")
    assert "crystal" in picks


# --- Substitution Token Tests ---


def test_resolve_substitution_token_matches():
    repo = _make_repo(
        ingredient_substitutions_by_token={
            "any:tag=calming&category=Botanical": {
                "token": "any:tag=calming&category=Botanical",
                "constraints": {
                    "category": "Botanical",
                    "tags": ["calming"],
                    "place_policy": "any_place",
                    "max_results": 10,
                },
                "fallback": "lemon_balm",
            },
        },
    )
    state = _make_state()

    result = resolve_substitution_token(
        "any:tag=calming&category=Botanical", state, repo, seed=42
    )

    assert result is not None
    assert result in repo.collectibles_by_id


def test_resolve_substitution_token_fallback():
    repo = _make_repo(
        collectibles_by_id={},  # No items to match
        ingredient_substitutions_by_token={
            "any:tag=rare": {
                "token": "any:tag=rare",
                "constraints": {
                    "category": None,
                    "tags": ["rare"],
                    "place_policy": "any_place",
                    "max_results": 10,
                },
                "fallback": "default_item",
            },
        },
    )
    state = _make_state()

    result = resolve_substitution_token("any:tag=rare", state, repo)
    assert result == "default_item"


def test_resolve_substitution_token_unknown_returns_none():
    repo = _make_repo()
    state = _make_state()

    result = resolve_substitution_token("any:nonexistent", state, repo)
    assert result is None


def test_resolve_substitution_same_place_locality():
    """same_place policy should only match items from the current place."""
    repo = _make_repo(
        places_by_id={
            "beach_tidepools": {
                "place_id": "beach_tidepools",
                "zone_id": "beach",
                "display_name": "Tidepools",
                "mood": "Observant",
                "is_threshold": True,
                "profile": {"player_need_satisfied": "Permission to notice"},
            },
        },
        collectibles_by_id={
            "tidepool_gem": {
                "collectible_id": "tidepool_gem",
                "item_type": "Crystal",
                "tags": ["wonder"],
                "origin_scope": "zone",
                "origin_ref": "beach_tidepools",
                "usable_in": ["spell"],
            },
            "forest_gem": {
                "collectible_id": "forest_gem",
                "item_type": "Crystal",
                "tags": ["wonder"],
                "origin_scope": "zone",
                "origin_ref": "forest",
                "usable_in": ["spell"],
            },
        },
        ingredient_substitutions_by_token={
            "any:place=beach_tidepools&tag=wonder": {
                "token": "any:place=beach_tidepools&tag=wonder",
                "constraints": {
                    "category": None,
                    "tags": ["wonder"],
                    "place_policy": "same_place",
                    "max_results": 10,
                },
                "fallback": "labradorite",
            },
        },
    )
    state = _make_state("beach_tidepools")

    result = resolve_substitution_token(
        "any:place=beach_tidepools&tag=wonder", state, repo, seed=1
    )

    assert result == "tidepool_gem"
