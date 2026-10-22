from __future__ import annotations

from dataclasses import replace

from idle_chapters.domain.conditions import evaluate_conditions
from idle_chapters.domain.effects import apply_effects
from idle_chapters.domain.encounters import meet, present_npcs
from idle_chapters.domain.errors import ActionNotEligible
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
            result = self._handle_enter(state, repo, seed)
        elif command == "choose option":
            result = self._handle_choose(state, choice_id, repo, seed)
        else:
            raise ValueError(f"Unknown command: {command}")
        result.visible_npcs = self.visible_npcs(result.new_state, repo)
        result.inventory = self.carrying(result.new_state, repo)
        return result

    @staticmethod
    def visible_npcs(state: PlayerState, repo) -> list[str]:
        return [n.get("display_name", n["npc_id"]) for n in present_npcs(state, repo)]

    @staticmethod
    def carrying(state: PlayerState, repo) -> list[str]:
        """What the player carries, by display name."""
        names = []
        for item_id, qty in state.inventory.items():
            name = getattr(repo, "collectibles_by_id", {}).get(item_id, {}).get("display_name", item_id.replace("_", " "))
            names.append(f"{name} ×{qty}" if qty > 1 else name)
        return names

    def _handle_enter(self, state: PlayerState, repo, seed, meeting: bool = True) -> StepResult:
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
            new_state, interaction_id, line = meet(new_state, repo, seed) if meeting else (new_state, None, None)

            entry_node = nodes_by_id.get(entry_node_id, {})
            action_ref = entry_node.get("action_ref")
            action = repo.actions_by_id.get(action_ref, {}) if action_ref else {}

            choices = self._with_paths(
                self._choices_from_node(entry_node, nodes_by_id, new_state, repo), new_state, repo
            )
            journal_page = self._render_journal(self._told_with(action, line), new_state, repo, seed=seed)

            return StepResult(
                journal_page=journal_page,
                choices=choices,
                new_state=new_state,
                debug={"seed": seed, "selected_scene_id": scene["scene_id"],
                       "interaction_id": interaction_id, "interaction_line": line},
            )
        else:
            candidates = generate_candidates(state, repo, seed, n=1)
            scene = candidates[0]

            new_state = replace(
                state,
                current_scene_id=scene.get("scene_id"),
                current_node_id=None,
            )
            new_state, interaction_id, line = meet(new_state, repo, seed) if meeting else (new_state, None, None)

            choices = self._with_paths(scene.get("choices", []), new_state, repo)
            told = {**scene, "prompt": self._told_with({"result": scene.get("prompt", "")}, line)["result"]}
            journal_page = self._render_journal_procedural(told, new_state, repo, seed=seed)

            return StepResult(
                journal_page=journal_page,
                choices=choices,
                new_state=new_state,
                debug={"seed": seed, "selected_scene_id": scene.get("scene_id"),
                       "interaction_id": interaction_id, "interaction_line": line},
            )

    def _handle_choose(
        self, state: PlayerState, choice_id: str | None, repo, seed
    ) -> StepResult:
        if not choice_id:
            raise ActionNotEligible(
                action_id="(none)",
                session_id=state.session_id,
                unmet_conditions=["choice_id is required"],
            )

        action = repo.actions_by_id.get(choice_id)

        # Procedural scenes have choices that aren't real actions.
        # Choosing one just cycles to a new scene; lingering is not arriving, so no one new speaks.
        if not action:
            if state.current_node_id is None:
                return self._handle_enter(self._tick(state), repo, seed, meeting=False)
            raise ActionNotEligible(
                action_id=choice_id,
                session_id=state.session_id,
                unmet_conditions=["action not found in current scene"],
            )

        if not evaluate_conditions(state, action.get("when"), repo):
            raise ActionNotEligible(
                action_id=choice_id,
                session_id=state.session_id,
                unmet_conditions=["when conditions not met"],
            )

        new_state = self._tick(apply_effects(state, action.get("effects", {})))

        if new_state.current_place_id != state.current_place_id:
            # A path: its own page tells the walk, then the destination takes over.
            arrived = self._handle_enter(new_state, repo, seed)
            arrival = self._entry_action(arrived.new_state, repo)
            if action.get("result") and arrival.get("result"):
                # An authored arrival (coming home) is told on the same page as the walk.
                action = {**action, "result": f"{action['result']} {arrival['result']}"}
            action = self._told_with(action, arrived.debug.get("interaction_line"))
            return StepResult(
                journal_page=self._render_journal(action, arrived.new_state, repo, seed=seed),
                choices=arrived.choices,
                new_state=arrived.new_state,
                debug={**arrived.debug, "choice_id": choice_id},
            )

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
            choices=self._with_paths(choices, new_state, repo),
            new_state=new_state,
            debug={"seed": seed, "choice_id": choice_id},
        )

    @staticmethod
    def _told_with(action: dict, line: str | None) -> dict:
        """The action, with what someone here said or did as its own paragraph."""
        if not line or not action:
            return action
        result = action.get("result")
        return {**action, "result": f"{result}\n\n{line}" if result else line}

    @staticmethod
    def _tick(state: PlayerState) -> PlayerState:
        """Doing something lets the day drift on; looking and resuming do not."""
        return replace(state, time_tick=state.time_tick + 1)

    @staticmethod
    def _with_paths(choices: list[dict], state: PlayerState, repo) -> list[dict]:
        """Every eligible way out of this place, after the scene's own choices."""
        offered = {c.get("action_id") for c in choices}
        paths = [
            {"action_id": a["action_id"], "label": a.get("label", a["action_id"])}
            for a in repo.actions_by_id.values()
            if (a.get("effects") or {}).get("move_to") not in (None, state.current_place_id)
            and a["action_id"] not in offered
            and evaluate_conditions(state, a.get("when"), repo)
        ]
        return [*choices, *paths]

    def choices_at(self, state: PlayerState, repo, seed: int | None = None) -> list[dict] | None:
        """Choices where the player left off, or None when they cannot be rebuilt.

        A procedural scene is rebuilt from the seed that rolled it.
        """
        if not state.current_node_id:
            if seed is None:
                return None
            rebuilt = self._handle_enter(state, repo, seed, meeting=False)
            if rebuilt.new_state.current_node_id or rebuilt.new_state.current_scene_id != state.current_scene_id:
                return None
            return rebuilt.choices
        scene = next(
            (s for s in repo.scenes_by_place_id.get(state.current_place_id, [])
             if s.get("scene_id") == state.current_scene_id),
            None,
        )
        if not scene:
            return None
        nodes_by_id = {n["node_id"]: n for n in scene.get("nodes", [])}
        node = nodes_by_id.get(state.current_node_id)
        if node is None:
            return None
        return self._with_paths(self._choices_from_node(node, nodes_by_id, state, repo), state, repo)

    def _find_current_scene(self, state: PlayerState, repo) -> dict | None:
        scenes = repo.scenes_by_place_id.get(state.current_place_id, [])
        if state.current_scene_id:
            for s in scenes:
                if s.get("scene_id") == state.current_scene_id:
                    return s
        if scenes:
            return scenes[0]
        return None

    @staticmethod
    def _entry_action(state: PlayerState, repo) -> dict:
        """The action at the entry node of the authored scene just entered, if any."""
        scene = next(
            (s for s in repo.scenes_by_place_id.get(state.current_place_id, [])
             if s.get("scene_id") == state.current_scene_id),
            None,
        )
        if not scene or not state.current_node_id:
            return {}
        node = next((n for n in scene.get("nodes", []) if n["node_id"] == state.current_node_id), {})
        return repo.actions_by_id.get(node.get("action_ref"), {})

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
        # Arriving is told as a walk (tea pages show the action's result); spells are for what you do once there.
        if place.get("is_threshold") and not action.get("effects", {}).get("move_to"):
            return "spell"

        return "tea"
