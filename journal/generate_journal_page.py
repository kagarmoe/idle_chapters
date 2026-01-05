#!/usr/bin/env python3
"""
Generate a cozy journal page that pulls from ingredients.json.

Usage:
  python generate_journal_page.py --ingredients ./lexicons/ingredients.json --places ./assets/places.json --place beach_tidepools --entry_type tea

Outputs Markdown to stdout (or --out path).
"""

from __future__ import annotations
import argparse, datetime, json, random, sys


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_place_zone_index(places_data: dict) -> dict[str, str]:
    """Return mapping of place_id -> zone_id from assets/places.json-style data."""
    idx: dict[str, str] = {}
    for p in places_data.get("places", []) or []:
        pid = p.get("place_id")
        zid = p.get("zone_id")
        if pid and zid:
            idx[pid] = zid
    return idx


def pick_ingredients(
    all_ingredients: list[dict],
    place_id: str,
    entry_type: str,
    n: int,
    place_to_zone: dict[str, str] | None = None,
) -> list[dict]:
    """Pick ingredients with strict locality.

    Order of preference:
      1) same_place (strict)
      2) same_zone (if place_to_zone available)
      3) same_element (derived from place or heuristic)
      4) global (any)
    """

    # 1) Same place (strict)
    same_place = [i for i in all_ingredients if i.get("place_id") == place_id]
    if len(same_place) >= n:
        return random.sample(same_place, n)

    # 2) Same zone (still local, but broader)
    same_zone: list[dict] = []
    if place_to_zone:
        current_zone = place_to_zone.get(place_id)
        if current_zone:
            same_zone = [
                i for i in all_ingredients
                if place_to_zone.get(i.get("place_id")) == current_zone
            ]
            # Prefer zone-local picks, but keep any same-place items already found.
            zone_candidates = list({id(x): x for x in (same_place + same_zone)}.values())
            if len(zone_candidates) >= n:
                return random.sample(zone_candidates, n)

    # 3) Same element (theme cohesion)
    element = None

    # Try to infer element from same-place items first (if any exist)
    for i in same_place:
        for t in i.get("tags", []):
            if isinstance(t, str) and t.startswith("element_"):
                element = t
                break
        if element:
            break

    if not element:
        # infer element from a place_id heuristic (safe fallback)
        if place_id.startswith("beach"):
            element = "element_water"
        elif place_id.startswith("forest"):
            element = "element_air"
        elif place_id.startswith("meadow") or place_id.endswith("shrine") or place_id.endswith("store"):
            element = "element_earth"
        else:
            element = "element_fire"

    same_element = [i for i in all_ingredients if element in i.get("tags", [])]

    # Keep already-local items (same_place + same_zone if computed), then add same-element.
    local_pool = same_place + (same_zone if same_zone else [])
    candidates = local_pool + same_element
    # Deduplicate by ingredient_id if present, else by object id.
    seen: set[str] = set()
    deduped: list[dict] = []
    for i in candidates:
        iid = i.get("ingredient_id")
        key = iid if isinstance(iid, str) else str(id(i))
        if key not in seen:
            seen.add(key)
            deduped.append(i)

    if len(deduped) >= n:
        return random.sample(deduped, n)

    return random.sample(all_ingredients, n)

def build_page(place_id: str, entry_type: str, picks: list[dict]) -> str:
    today = datetime.date.today().isoformat()
    need = picks[0].get("player_need_satisfied", "A gentle need")
    mood = {
        "tea": "soft",
        "spell": "tender",
        "field_note": "curious",
        "dream_fragment": "hushed"
    }.get(entry_type, "soft")

    ingredient_names = [p["display_name"] for p in picks]
    tags = sorted({t for p in picks for t in p.get("tags", []) if not t.startswith("element_")})

    prompt = {
        "tea": "What softened today? What can wait until tomorrow?",
        "spell": "Name a feeling gently. Give it a home. Let it change shape.",
        "field_note": "What did I notice that I would have missed yesterday?",
        "dream_fragment": "What returned in a kinder shape while I slept?"
    }.get(entry_type, "Write one true thing, gently.")

    body_lines = [
        f"I’m at **{place_id}**.",
        f"Today’s need: *{need}*.",
        "",
        "I chose: " + ", ".join(f"**{n}**" for n in ingredient_names) + ".",
        "",
        "A small sensory detail: ________________________________",
        "",
        "Because: _______________________________________________",
        "",
        "What I’m keeping (one sentence): ________________________",
    ]

    frontmatter = [
        "---",
        f"page_id: {place_id}_{entry_type}_{today.replace('-','')}_{random.randint(1000,9999)}",
        f"date: {today}",
        f"place_id: {place_id}",
        f"entry_type: {entry_type}",
        f"mood: {mood}",
        f"need: \"{need}\"",
        "ingredients:",
    ] + [f"  - {p['ingredient_id']}" for p in picks] + [
        "tags:",
    ] + [f"  - {t}" for t in tags] + [
        "---",
        ""
    ]

    md = "\n".join(frontmatter) + f"## Prompt\n{prompt}\n\n## Entry\n" + "\n".join(body_lines) + "\n"
    return md

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ingredients", required=True, help="Path to ingredients.json")
    ap.add_argument("--places", default=None, help="Path to assets/places.json (optional; enables same_zone selection)")
    ap.add_argument("--place", required=True, help="place_id")
    ap.add_argument("--entry_type", default="tea", choices=["tea","spell","field_note","dream_fragment"])
    ap.add_argument("--n", type=int, default=3, help="How many ingredients to include")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None, help="Output markdown file path (optional)")
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    data = load_json(args.ingredients)
    place_to_zone = None
    if args.places:
        places_data = load_json(args.places)
        place_to_zone = build_place_zone_index(places_data)
    all_ingredients = data.get("ingredients", [])
    if not all_ingredients:
        raise SystemExit("No ingredients found.")

    picks = pick_ingredients(all_ingredients, args.place, args.entry_type, args.n, place_to_zone=place_to_zone)
    md = build_page(args.place, args.entry_type, picks)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md)
    else:
        sys.stdout.write(md)

if __name__ == "__main__":
    main()
