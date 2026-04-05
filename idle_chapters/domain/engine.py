from __future__ import annotations

from dataclasses import replace

from idle_chapters.domain.conditions import evaluate_conditions
from idle_chapters.domain.effects import apply_effects
from idle_chapters.domain.ingredient_picker import pick_ingredients
from idle_chapters.domain.journal_renderer import render_journal_page
from idle_chapters.domain.selector import (
    choose_scene,
    eligible_scenes,
    generate_candidates,
)
from idle_chapters.domain.state import PlayerState
from idle_chapters.domain.step_result import StepResult


class Engine:

    def step(
        self,
        state: PlayerState,
        command: str,
        choice_id: str | None,
        repo,
        seed: int | None = None,
    ) -> StepResult:
        if command == "enter":
            return self._handle_enter(state, repo, seed)
        elif command == "choose option":
            return self._handle_choose(state, choice_id, repo, seed)
        else:
            raise ValueError(f"Unknown command: {command}")

    def _handle_enter(self, state: PlayerState, repo, seed) -> StepResult:
        authored = eligible_scenes(state, repo)

        if authored:
            scene = choose_scene(authored, seed)
            entry_node_id = scene.get("entry_node")
            nodes_by_id = {n["node_id"]: n for n in scene.get("nodes", [])}

            new_state = replace(
                state,
                current_scene_id=scene["scene_id"],
                current_node_id=entry_node_id,
            )

            entry_node = nodes_by_id.get(entry_node_id, {})
            action_ref = entry_node.get("action_ref")
            action = repo.actions_by_id.get(action_ref, {}) if action_ref else {}

            choices = self._choices_from_node(entry_node, nodes_by_id, new_state, repo)
            journal_page = self._render_journal(action, new_state, repo, seed=seed)

            return StepResult(
                journal_page=journal_page,
                choices=choices,
                new_state=new_state,
                debug={"seed": seed, "selected_scene_id": scene["scene_id"]},
            )
        else:
            candidates = generate_candidates(state, repo, seed, n=1)
            scene = candidates[0]

            new_state = replace(
                state,
                current_scene_id=scene.get("scene_id"),
                current_node_id=None,
            )

            choices = scene.get("choices", [])
            journal_page = self._render_journal_procedural(scene, new_state, repo, seed=seed)

            return StepResult(
                journal_page=journal_page,
                choices=choices,
                new_state=new_state,
                debug={"seed": seed, "selected_scene_id": scene.get("scene_id")},
            )

    def _handle_choose(
        self, state: PlayerState, choice_id: str | None, repo, seed
    ) -> StepResult:
        if not choice_id:
            raise ValueError("choice_id required for 'choose option' command")

        action = repo.actions_by_id.get(choice_id)

        # Procedural scenes have choices that aren't real actions.
        # Choosing one just cycles to a new scene.
        if not action:
            if state.current_node_id is None:
                return self._handle_enter(state, repo, seed)
            raise ValueError(f"Unknown action: {choice_id}")

        new_state = apply_effects(state, action.get("effects", {}))

        scene = self._find_current_scene(state, repo)
        choices: list[dict] = []

        if scene and scene.get("nodes"):
            nodes_by_id = {n["node_id"]: n for n in scene["nodes"]}
            target_node = self._find_node_by_action(nodes_by_id, choice_id)

            if target_node:
                new_state = replace(
                    new_state,
                    current_scene_id=scene["scene_id"],
                    current_node_id=target_node["node_id"],
                )
                choices = self._choices_from_node(
                    target_node, nodes_by_id, new_state, repo
                )

        journal_page = self._render_journal(action, new_state, repo, seed=seed)

        return StepResult(
            journal_page=journal_page,
            choices=choices,
            new_state=new_state,
            debug={"seed": seed, "choice_id": choice_id},
        )

    def _find_current_scene(self, state: PlayerState, repo) -> dict | None:
        scenes = repo.scenes_by_place_id.get(state.current_place_id, [])
        if state.current_scene_id:
            for s in scenes:
                if s.get("scene_id") == state.current_scene_id:
                    return s
        if scenes:
            return scenes[0]
        return None

    def _find_node_by_action(
        self, nodes_by_id: dict, action_id: str
    ) -> dict | None:
        for node in nodes_by_id.values():
            if node.get("action_ref") == action_id:
                return node
        return None

    def _choices_from_node(
        self, node: dict, nodes_by_id: dict, state: PlayerState, repo
    ) -> list[dict]:
        choices = []
        for next_node_id in node.get("choices", []):
            next_node = nodes_by_id.get(next_node_id)
            if not next_node:
                continue
            action_ref = next_node.get("action_ref")
            action = repo.actions_by_id.get(action_ref) if action_ref else None
            if action and evaluate_conditions(state, action.get("when"), repo):
                choices.append({
                    "action_id": action["action_id"],
                    "label": action.get("label", action_ref),
                })
        return choices

    def _render_journal(
        self, action: dict, state: PlayerState, repo, seed: int | None = None
    ) -> dict | None:
        if not action:
            return None

        entry_type = self._infer_entry_type(action, state, repo)
        ingredient_ids = pick_ingredients(state, repo, entry_type, seed=seed)

        return render_journal_page(
            place_id=state.current_place_id,
            entry_type=entry_type,
            action=action,
            state=state,
            repo=repo,
            ingredient_picks=ingredient_ids,
            seed=seed,
        )

    def _render_journal_procedural(
        self, scene: dict, state: PlayerState, repo, seed: int | None = None
    ) -> dict | None:
        entry_type = scene.get("entry_type", "field_note")
        ingredient_ids = pick_ingredients(state, repo, entry_type, seed=seed)

        action_proxy = {
            "action_id": scene.get("scene_id"),
            "result": scene.get("prompt", ""),
        }

        return render_journal_page(
            place_id=state.current_place_id,
            entry_type=entry_type,
            action=action_proxy,
            state=state,
            repo=repo,
            ingredient_picks=ingredient_ids,
            seed=seed,
        )

    @staticmethod
    def _infer_entry_type(action: dict, state: PlayerState, repo) -> str:
        """Infer entry_type from action tags or place properties."""
        intent = action.get("intent_signature", {})
        if intent.get("entry_type"):
            return intent["entry_type"]

        tags = set(action.get("tags", []))
        if "tea" in tags:
            return "tea"
        if "spell" in tags:
            return "spell"

        place = repo.places_by_id.get(state.current_place_id, {})
        if place.get("is_threshold"):
            return "spell"

        return "tea"
