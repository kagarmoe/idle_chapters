"""Journal renderer: transforms game state + template into a JournalPage.

Produces frontmatter + markdown body conforming to journal_page.schema.json.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JournalPage:
    """A rendered journal page matching journal_page.schema fields."""

    page_id: str
    date: str
    place_id: str
    entry_type: str
    mood: str
    need: str
    ingredients: list[str]
    prompt: str
    body: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "date": self.date,
            "place_id": self.place_id,
            "entry_type": self.entry_type,
            "mood": self.mood,
            "need": self.need,
            "ingredients": list(self.ingredients),
            "prompt": self.prompt,
            "body": self.body,
            "tags": list(self.tags),
        }


def render_journal_page(
    place_id: str,
    entry_type: str,
    action: dict[str, Any] | None,
    state,
    repo,
    ingredient_picks: list[str] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Render a complete journal page from template + context.

    Returns a dict matching journal_page.schema.json (the inner object,
    not the wrapper).
    """
    template = _select_template(repo, entry_type, seed)
    place = repo.places_by_id.get(place_id, {})

    mood = _resolve_mood(template, place)
    need = _resolve_need(template, place)
    prompt = template.get("prompt", "What happened here?")
    structure = template.get("structure", [])

    ingredients = ingredient_picks or []
    body = _assemble_body(
        structure=structure,
        place=place,
        action=action,
        ingredients=ingredients,
        repo=repo,
        entry_type=entry_type,
    )

    page_id = _generate_page_id(place_id, entry_type, seed)
    date = _current_date()

    page = JournalPage(
        page_id=page_id,
        date=date,
        place_id=place_id,
        entry_type=entry_type,
        mood=mood,
        need=need,
        ingredients=ingredients,
        prompt=prompt,
        body=body,
        tags=template.get("tags", []),
    )

    return page.to_dict()


def _select_template(
    repo, entry_type: str, seed: int | None = None
) -> dict[str, Any]:
    """Select a journal template for the given entry_type."""
    templates = repo.journal_templates_by_entry_type.get(entry_type, [])
    if not templates:
        return {
            "template_id": f"fallback_{entry_type}",
            "entry_type": entry_type,
            "prompt": "What happened here?",
            "structure": ["A moment passed quietly."],
            "tags": [],
        }

    if seed is not None and len(templates) > 1:
        idx = seed % len(templates)
        return templates[idx]

    return templates[0]


def _resolve_mood(template: dict[str, Any], place: dict[str, Any]) -> str:
    """Determine mood from template hint or place profile."""
    mood_hint = template.get("mood_hint")
    if mood_hint:
        return mood_hint

    return place.get("mood", "Calm")


def _resolve_need(template: dict[str, Any], place: dict[str, Any]) -> str:
    """Determine player need from template hint or place profile."""
    need_hint = template.get("need_hint")
    if need_hint:
        return need_hint

    profile = place.get("profile", {})
    return profile.get("player_need_satisfied", "Permission to rest")


def _assemble_body(
    structure: list[str],
    place: dict[str, Any],
    action: dict[str, Any] | None,
    ingredients: list[str],
    repo,
    entry_type: str,
) -> str:
    """Assemble the markdown body from template structure and context."""
    lines: list[str] = []

    place_name = place.get("display_name", "a quiet place")
    action_result = ""
    if action:
        action_result = action.get("result", "")
        if not action_result:
            variants = action.get("result_variants", [])
            action_result = variants[0] if variants else ""

    ingredient_names = _resolve_ingredient_names(ingredients, repo)

    for section_hint in structure:
        line = _render_section(
            section_hint,
            place_name=place_name,
            action_result=action_result,
            ingredient_names=ingredient_names,
            entry_type=entry_type,
        )
        lines.append(line)

    if not lines:
        lines.append(f"A quiet moment at {place_name}.")

    return "\n\n".join(lines)


def _render_section(
    hint: str,
    place_name: str,
    action_result: str,
    ingredient_names: list[str],
    entry_type: str,
) -> str:
    """Render a single body section guided by the template hint."""
    hint_lower = hint.lower()

    if "sensory" in hint_lower or "place" in hint_lower or "where" in hint_lower:
        return f"At {place_name}, the air carries something familiar."

    if "ingredient" in hint_lower or "chose" in hint_lower:
        if ingredient_names:
            joined = ", ".join(ingredient_names)
            return f"Today I gathered {joined}."
        return "The ingredients found themselves, as they do."

    if "carry" in hint_lower or "forward" in hint_lower:
        if action_result:
            return action_result
        return "Something small to hold onto."

    if "asking" in hint_lower or "feeling" in hint_lower or "intent" in hint_lower:
        return "A gentle asking, without urgency."

    if "blessing" in hint_lower or "closing" in hint_lower:
        return "May this settle where it needs to."

    if "observation" in hint_lower or "notice" in hint_lower or "tiny" in hint_lower:
        return f"Something small caught my eye at {place_name}."

    if "connection" in hint_lower or "quiet" in hint_lower:
        return "A thread between this moment and the last."

    if "question" in hint_lower or "revisit" in hint_lower:
        return "I wonder if this will look different tomorrow."

    if "list" in hint_lower or "inventory" in hint_lower or "journal" in hint_lower:
        if ingredient_names:
            items = "\n".join(f"- {name}" for name in ingredient_names)
            return f"What I carry:\n{items}"
        return "My pack holds what it holds."

    if "favorite" in hint_lower or "note" in hint_lower:
        return "Each thing here has its own small weight."

    if "reminder" in hint_lower or "enough" in hint_lower or "need" in hint_lower:
        return "I have what I need."

    if action_result:
        return action_result

    return hint


def _resolve_ingredient_names(
    ingredient_ids: list[str], repo
) -> list[str]:
    """Look up display names for ingredient collectible_ids."""
    names = []
    for item_id in ingredient_ids:
        item = repo.collectibles_by_id.get(item_id, {})
        name = item.get("display_name", item_id.replace("_", " "))
        names.append(name)
    return names


def _generate_page_id(place_id: str, entry_type: str, seed: int | None) -> str:
    """Generate a deterministic page_id."""
    raw = f"{place_id}_{entry_type}_{seed or int(time.time())}"
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"jp_{short_hash}"


def _current_date() -> str:
    """Return current date as YYYY-MM-DD string."""
    from datetime import date
    return date.today().isoformat()
