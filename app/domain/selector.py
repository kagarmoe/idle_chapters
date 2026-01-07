from __future__ import annotations

import random
from typing import Iterable

from app.domain.storylet_generator import generate_storylet


def generate_candidates(state, repo, seed: int | None, n: int = 3) -> list[dict]:
    rng = random.Random(seed)
    candidates = []
    for _ in range(n):
        candidate_seed = rng.randint(0, 1_000_000) if seed is not None else None
        candidate = generate_storylet(state=state, repo=repo, seed=candidate_seed)
        candidates.append(candidate.to_dict() if hasattr(candidate, "to_dict") else candidate)
    return candidates


def merge_with_authored(candidates: Iterable[dict], authored: Iterable[dict]) -> list[dict]:
    merged = list(authored) + list(candidates)
    return merged


def eligible_scenes(state, repo) -> list[dict]:
    """Get scenes eligible for the current place."""
    return list(repo.scenes_by_place_id.get(state.current_place_id, []))


def eligible_actions(state, repo) -> list[dict]:
    """Get actions eligible for the current state (basic implementation)."""
    # TODO: implement full condition evaluation
    return list(repo.actions_by_id.values())


def choose_scene(scenes: list[dict], seed: int | None = None) -> dict:
    if not scenes:
        raise ValueError("No eligible scenes")
    rng = random.Random(seed)
    return rng.choice(scenes)
