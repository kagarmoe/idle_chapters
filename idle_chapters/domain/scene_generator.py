from __future__ import annotations

import random
from typing import Any

from idle_chapters.domain.errors import InvalidLocation
from idle_chapters.domain.scene import Scene


# Each family is shaped like one structural interaction type (interactions_design.md §2):
# (interaction_type, the senses it can draw on, its sentence). {A}/{a} is a sensory anchor.
FAMILIES = {
    "arrival": ("ambient_ack", ("sight", "smell", "sound"), "{A}, all around you."),
    "small_find": ("light_request", ("sight",), "Near the {a}, something small catches your eye."),
    "offer_help": ("micro_offer", ("sight", "smell", "sound"), "{A}. There is a good spot to sit, if you would like one."),
    "quiet_notice": ("ambient_ack", ("sight", "smell", "sound"), "For a moment there is only {a}."),
    "threshold_call": ("threshold_adjacent", ("sight",), "Past the {a}, the way goes on. It will keep."),
}

# Choices in a generated scene: lingering, never a task. Each tells what you did on the next page.
CHOICES = {
    "pause_and_breathe": ("Pause and breathe", "You pause and breathe in slowly, letting the moment be what it is."),
    "notice_a_detail": ("Notice a detail", "You let your eyes rest on one small thing for as long as you like."),
    "sip_and_reflect": ("Sip and reflect", "You take a slow sip of water and let your thoughts wander where they will."),
    "wander_softly": ("Wander softly", "You wander a few easy steps, with nowhere you need to be."),
    "listen_closely": ("Listen closely", "You listen for a while. Small sounds come and go."),
    "jot_a_small_note": ("Jot a small note", "You jot a line or two in the margin of your journal."),
}

_PHRASE = {"sight": "{w}", "smell": "the smell of {w}", "sound": "the sound of {w}"}


def _not_allowed_words(repo) -> set[str]:
    words = set()
    for entry in repo.lexicon_by_key.values():
        if entry.get("lexicon_type") == "Not_Allowed":
            words.update(word.lower() for word in entry.get("words", []))
    return words


def _sensory_words(repo, place_id: str, zone_id: str | None, disallowed: set[str]) -> list[tuple[str, str]]:
    """(sense, word) pairs for this place, from lexicon keys like smell_forest; never a not-allowed word."""
    pairs = []
    for key, entry in repo.lexicon_by_key.items():
        sense = str(entry.get("key", key)).split("_")[0]
        if entry.get("lexicon_type") != "Sensory" or sense not in _PHRASE:
            continue
        if entry.get("scope") in ("Global", place_id, zone_id):
            pairs += [(sense, w) for w in entry.get("words", []) if all(bad not in w.lower() for bad in disallowed)]
    return pairs


def _prompt(family: str, pairs: list[tuple[str, str]], repo, rng: random.Random) -> str:
    _, senses, sentence = FAMILIES[family]
    usable = [(s, w) for s, w in pairs if s in senses]
    if not usable:
        feelings = [w for e in repo.lexicon_by_key.values() if e.get("lexicon_type") == "Emotion" for w in e.get("words", [])]
        return f"Everything here feels {rng.choice(feelings)}." if feelings else "A quiet moment, just as it is."
    sense, word = rng.choice(usable)
    anchor = _PHRASE[sense].format(w=word)
    return sentence.format(A=anchor[0].upper() + anchor[1:], a=anchor)


def _choices(rng: random.Random) -> list[dict[str, Any]]:
    return [{"choice_id": cid, "label": CHOICES[cid][0], "effects": {}} for cid in rng.sample(sorted(CHOICES), k=3)]


def generate_scene(state, repo, seed: int | None = None) -> Scene:
    if state.current_place_id not in repo.places_by_id:
        raise InvalidLocation(location_id=state.current_place_id)

    place = repo.places_by_id[state.current_place_id]
    zone_id = place.get("zone_id")
    rng = random.Random(seed)

    entry_type = "spell" if place.get("is_threshold") else "tea"
    family = rng.choice(sorted(FAMILIES))

    pairs = _sensory_words(repo, state.current_place_id, zone_id, _not_allowed_words(repo))
    prompt = _prompt(family, pairs, repo, rng)

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
            "interaction_type": FAMILIES[family][0],
            "template_id": "procedural_v2",
            "notes": "generated",
        },
    )

    # Note: scene.schema.json is for authored scenes (entry_node + nodes shape).
    # Procedural Scene uses a different shape (choices + prompt), so we skip
    # schema validation here. Authored scenes are validated at content load time.

    return scene
