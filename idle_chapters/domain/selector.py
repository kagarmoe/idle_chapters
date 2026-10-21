from __future__ import annotations

import random
from typing import Iterable

from idle_chapters.domain.errors import SceneNotAvailable
from idle_chapters.domain.scene_generator import generate_scene


def generate_candidates(state, repo, seed: int | None, n: int = 3) -> list[dict]:
    rng = random.Random(seed)
    candidates = []
    for _ in range(n):
        candidate_seed = rng.randint(0, 1_000_000) if seed is not None else None
        candidate = generate_scene(state=state, repo=repo, seed=candidate_seed)
        candidates.append(candidate.to_dict() if hasattr(candidate, "to_dict") else candidate)
    return candidates


def merge_with_authored(candidates: Iterable[dict], authored: Iterable[dict]) -> list[dict]:
    merged = list(authored) + list(candidates)
    return merged


def eligible_scenes(state, repo) -> list[dict]:
    """Scenes at the current place whose entry action may happen now."""
    from idle_chapters.domain.conditions import evaluate_conditions

    def opens(scene: dict) -> bool:
        # The scene schema has no `when`; a scene is gated by its entry node's action instead.
        entry = next((n for n in scene.get("nodes", []) if n.get("node_id") == scene.get("entry_node")), {})
        action = repo.actions_by_id.get(entry.get("action_ref"))
        return action is None or evaluate_conditions(state, action.get("when"), repo)

    return [s for s in repo.scenes_by_place_id.get(state.current_place_id, []) if opens(s)]


def eligible_actions(state, repo) -> list[dict]:
    """Get actions eligible for the current state with full condition evaluation."""
    from idle_chapters.domain.conditions import evaluate_conditions

    return [
        a for a in repo.actions_by_id.values()
        if evaluate_conditions(state, a.get("when"), repo)
    ]


def choose_scene(scenes: list[dict], seed: int | None = None) -> dict:
    if not scenes:
        raise SceneNotAvailable(session_id="")
    rng = random.Random(seed)
    return rng.choice(scenes)
