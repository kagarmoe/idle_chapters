"""Free-text intent: which offered choice a player's words mean (CLI_INTENT_PARSING.md)."""

from __future__ import annotations

import re
from collections.abc import Iterable

_JOINER = "\x00"


def normalize(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s',]", " ", text.lower()).split())


def split_clauses(text: str, keep: Iterable[str] = ()) -> list[str]:
    """Split on "and", "then" and commas, but never inside a known phrase or label."""
    t = normalize(text)
    for phrase in keep:
        p = normalize(phrase)
        if " and " in p:
            t = t.replace(p, p.replace(" and ", f" {_JOINER} "))
    parts = re.split(r",|\bthen\b|\band\b", t)
    return [" ".join(p.replace(_JOINER, "and").split()) for p in parts if p.strip(" ,")]


def match_intent(clause: str, choices: list[dict], repo) -> str | None:
    """The best offered choice for one clause: a phrase or label beats a keyword; longer beats shorter."""
    padded = f" {normalize(clause).replace(',', ' ')} "
    best, best_score = None, (0, 0)
    for choice in choices:
        choice_id = choice.get("action_id") or choice.get("choice_id")
        sig = (repo.actions_by_id.get(choice_id) or {}).get("intent_signature", {})
        phrases = [*sig.get("phrases", []), choice.get("label", "")]
        scores = [(2, len(p)) for p in map(normalize, phrases) if p and f" {p} " in padded]
        scores += [(1, len(k)) for k in map(normalize, sig.get("keywords", [])) if k and f" {k} " in padded]
        score = max(scores, default=(0, 0))
        if score > best_score:
            best, best_score = choice_id, score
    return best
