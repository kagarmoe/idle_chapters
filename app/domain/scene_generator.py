from __future__ import annotations

import random
from typing import Any

from app.domain.scene import Scene


FAMILIES = [
    "arrival",
    "small_find",
    "offer_help",
    "quiet_notice",
    "threshold_call",
]

SAFE_CHOICE_LABELS = [
    "Pause and breathe",
    "Notice a detail",
    "Sip and reflect",
    "Wander softly",
    "Listen closely",
    "Jot a small note",
]


def _not_allowed_words(repo) -> set[str]:
    words = set()
    for entry in repo.lexicon_by_key.values():
        if entry.get("lexicon_type") == "Not_Allowed":
            words.update(word.lower() for word in entry.get("words", []))
    return words


def _descriptive_words(repo, place_id: str, zone_id: str | None) -> list[str]:
    words: list[str] = []
    for entry in repo.lexicon_by_key.values():
        if entry.get("lexicon_type") != "Sensory":
            continue
        scope = entry.get("scope")
        if scope in ("Global", place_id, zone_id):
            words.extend(entry.get("words", []))
    return words


def _safe_prompt(words: list[str], disallowed: set[str], rng: random.Random) -> str:
    filtered = [word for word in words if all(bad not in word.lower() for bad in disallowed)]
    if not filtered:
        return "A quiet detail catches the eye."
    chosen = rng.choice(filtered)
    return f"{chosen} lingers nearby."


def _choices(rng: random.Random) -> list[dict[str, Any]]:
    labels = rng.sample(SAFE_CHOICE_LABELS, k=3)
    return [
        {"choice_id": "1", "label": labels[0], "effects": {}},
        {"choice_id": "2", "label": labels[1], "effects": {}},
        {"choice_id": "3", "label": labels[2], "effects": {}},
    ]


def generate_scene(state, repo, seed: int | None = None) -> Scene:
    if state.current_place_id not in repo.places_by_id:
        raise ValueError(f"Unknown place_id: {state.current_place_id}")

    place = repo.places_by_id[state.current_place_id]
    zone_id = place.get("zone_id")
    rng = random.Random(seed)

    entry_type = "spell" if place.get("is_threshold") else "tea"
    family = rng.choice(FAMILIES)

    disallowed = _not_allowed_words(repo)
    words = _descriptive_words(repo, state.current_place_id, zone_id)
    prompt = _safe_prompt(words, disallowed, rng)

    scene_id = f"{state.current_place_id}_{entry_type}_{family}"
    if seed is not None:
        scene_id = f"{scene_id}_{seed}"

    scene = Scene(
        scene_id=scene_id,
        place_id=state.current_place_id,
        entry_type=entry_type,
        title=None,
        prompt=prompt,
        tags=[entry_type],
        need_hint="Gentle rest" if entry_type == "tea" else "Soft resolve",
        mood_hint="Calm",
        conditions={},
        choices=_choices(rng),
        debug={
            "seed": str(seed) if seed is not None else "none",
            "family_id": family,
            "template_id": "procedural_v1",
            "notes": "generated",
        },
    )

    # Note: scene.schema.json is for authored scenes (entry_node + nodes shape).
    # Procedural Scene uses a different shape (choices + prompt), so we skip
    # schema validation here. Authored scenes are validated at content load time.

    return scene
