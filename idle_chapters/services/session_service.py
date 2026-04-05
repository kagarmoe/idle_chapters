from __future__ import annotations

from uuid import uuid4

from idle_chapters.domain.engine import Engine
from idle_chapters.domain.state import PlayerState
from idle_chapters.domain.step_result import StepResult


class SessionService:
    """Bridge between API routers (or CLI) and the domain engine.

    Plain Python — no FastAPI imports. Reusable by any interface.
    """

    def __init__(self, repo, engine: Engine, state_store, journal_store, event_store):
        self._repo = repo
        self._engine = engine
        self._state_store = state_store
        self._journal_store = journal_store
        self._event_store = event_store

    def create_session(self, place_id: str = "cottage_home") -> tuple[str, StepResult]:
        """Create a new session and enter the starting place."""
        session_id = uuid4().hex

        state = PlayerState(
            session_id=session_id,
            current_place_id=place_id,
            inventory={},
            flags=set(),
            time_tick=0,
        )

        result = self._engine.step(state, "enter", None, self._repo)
        self._persist(session_id, result)

        return session_id, result

    def enter(self, session_id: str) -> StepResult:
        """Re-enter the current place (refresh scene)."""
        state = self._load_state(session_id)
        result = self._engine.step(state, "enter", None, self._repo)
        self._persist(session_id, result)
        return result

    def perform_action(self, session_id: str, action_id: str) -> StepResult:
        """Execute a chosen action."""
        state = self._load_state(session_id)
        result = self._engine.step(state, "choose option", action_id, self._repo)
        self._persist(session_id, result)
        return result

    def submit_intent(self, session_id: str, text: str) -> StepResult:
        """Match free-text input to an eligible action and execute it."""
        state = self._load_state(session_id)

        # Get current choices to match against
        current_result = self._engine.step(state, "enter", None, self._repo)
        matched_id = self._match_intent(text, current_result.choices)

        if matched_id is None:
            raise ValueError(f"No eligible action matched intent: {text!r}")

        result = self._engine.step(state, "choose option", matched_id, self._repo)
        self._persist(session_id, result)
        return result

    def get_session(self, session_id: str) -> PlayerState | None:
        """Load and return current player state, or None if not found."""
        return self._state_store.get_state(session_id)

    def _load_state(self, session_id: str) -> PlayerState:
        state = self._state_store.get_state(session_id)
        if state is None:
            raise ValueError(f"Session not found: {session_id}")
        return state

    def _persist(self, session_id: str, result: StepResult) -> None:
        self._state_store.upsert_state(session_id, result.new_state)

        if result.journal_page:
            self._journal_store.append_page(session_id, result.journal_page)

        self._event_store.append_event(session_id, {
            "event_type": "step",
            "data": {
                "scene_id": result.debug.get("selected_scene_id") if result.debug else None,
                "choice_id": result.debug.get("choice_id") if result.debug else None,
            },
        })

    @staticmethod
    def _match_intent(text: str, choices: list[dict]) -> str | None:
        """Match free-text input against choice labels."""
        text_lower = text.lower()
        for choice in choices:
            label = choice.get("label", "").lower()
            if label and label in text_lower:
                return choice.get("action_id") or choice.get("choice_id")
        return None
