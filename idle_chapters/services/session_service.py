from __future__ import annotations

import logging
from uuid import uuid4

from idle_chapters.domain.engine import Engine
from idle_chapters.domain.errors import (
    ActionNotEligible,
    InsufficientInventory,
    IntentNoMatch,
    InvalidLocation,
    SceneNotAvailable,
    SessionNotFound,
)
from idle_chapters.domain.state import PlayerState
from idle_chapters.domain.step_result import StepResult
from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery

logger = logging.getLogger(__name__)


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

        try:
            result = self._engine.step(state, "enter", None, self._repo)
        except (SceneNotAvailable, InvalidLocation) as e:
            raise self._domain_error(e) from e
        except Exception as e:
            raise self._engine_error(session_id, e) from e

        self._persist(session_id, result, is_new_session=True)
        return session_id, result

    def enter(self, session_id: str) -> StepResult:
        """Re-enter the current place (refresh scene)."""
        state = self._load_state(session_id)

        try:
            result = self._engine.step(state, "enter", None, self._repo)
        except (SceneNotAvailable, InvalidLocation) as e:
            raise self._domain_error(e) from e
        except Exception as e:
            raise self._engine_error(session_id, e) from e

        self._persist(session_id, result)
        return result

    def perform_action(self, session_id: str, action_id: str) -> StepResult:
        """Execute a chosen action."""
        state = self._load_state(session_id)

        try:
            result = self._engine.step(state, "choose option", action_id, self._repo)
        except (ActionNotEligible, InsufficientInventory, InvalidLocation,
                SceneNotAvailable) as e:
            raise self._domain_error(e) from e
        except Exception as e:
            raise self._engine_error(session_id, e) from e

        self._persist(session_id, result)
        return result

    def submit_intent(self, session_id: str, text: str) -> StepResult:
        """Match free-text input to an eligible action and execute it."""
        state = self._load_state(session_id)

        try:
            current_result = self._engine.step(state, "enter", None, self._repo)
        except Exception as e:
            raise self._engine_error(session_id, e) from e

        matched_id = self._match_intent(text, current_result.choices)

        if matched_id is None:
            available = [c.get("label", "") for c in current_result.choices]
            raise GameError(
                kind=ErrorKind.INTENT_NO_MATCH,
                effect=Effect.NONE,
                recovery=Recovery.CORRECTABLE,
                detail=(
                    f"WHAT: No action matched intent {text!r} for session {session_id}.\n"
                    f"MEANS: State unchanged. Available actions: {available}.\n"
                    f"DO: Rephrase or choose from eligible actions."
                ),
                context={
                    "input": text,
                    "available_actions": ", ".join(available),
                    "session_id": session_id,
                },
            )

        try:
            result = self._engine.step(state, "choose option", matched_id, self._repo)
        except (ActionNotEligible, InsufficientInventory, InvalidLocation,
                SceneNotAvailable) as e:
            raise self._domain_error(e) from e
        except Exception as e:
            raise self._engine_error(session_id, e) from e

        self._persist(session_id, result)
        return result

    def get_session(self, session_id: str) -> PlayerState | None:
        """Load and return current player state, or None if not found."""
        return self._state_store.get_state(session_id)

    # ---- internal helpers ----

    def _load_state(self, session_id: str) -> PlayerState:
        state = self._state_store.get_state(session_id)
        if state is None:
            raise GameError(
                kind=ErrorKind.SESSION_NOT_FOUND,
                effect=Effect.NONE,
                recovery=Recovery.TERMINAL,
                detail=(
                    f"WHAT: No session exists for {session_id}.\n"
                    f"MEANS: Nothing was modified.\n"
                    f"DO: Create a new session via POST /v1/sessions."
                ),
                context={"session_id": session_id},
            )
        return state

    def _persist(
        self, session_id: str, result: StepResult, *, is_new_session: bool = False,
    ) -> None:
        try:
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
        except Exception as e:
            effect = Effect.NONE if is_new_session else Effect.PARTIAL
            means = (
                "Session was never persisted. No prior state was corrupted."
                if is_new_session
                else "Player state was computed but not persisted. In-memory and database have diverged."
            )
            logger.exception("Persistence failure for session %s", session_id)
            raise GameError(
                kind=ErrorKind.PERSISTENCE_FAILURE,
                effect=effect,
                recovery=Recovery.RETRYABLE,
                detail=(
                    f"WHAT: Write failed after engine applied effects to session {session_id}.\n"
                    f"MEANS: {means}\n"
                    f"DO: Retry the request. If it persists, check database connectivity."
                ),
                context={"session_id": session_id},
            ) from e

    def _domain_error(self, exc: Exception) -> GameError:
        """Map a typed domain exception to a GameError."""
        if isinstance(exc, ActionNotEligible):
            return GameError(
                kind=ErrorKind.ACTION_NOT_ELIGIBLE,
                effect=Effect.NONE,
                recovery=Recovery.CORRECTABLE,
                detail=(
                    f"WHAT: Action {exc.action_id} failed conditions for session {exc.session_id}.\n"
                    f"MEANS: State unchanged. Action requires unmet conditions.\n"
                    f"DO: Check eligible actions via GET /v1/sessions/{exc.session_id}."
                ),
                context={
                    "action_id": exc.action_id,
                    "session_id": exc.session_id,
                    "unmet": exc.unmet_conditions,
                },
            )
        if isinstance(exc, InsufficientInventory):
            return GameError(
                kind=ErrorKind.INSUFFICIENT_INVENTORY,
                effect=Effect.NONE,
                recovery=Recovery.CORRECTABLE,
                detail=(
                    f"WHAT: Insufficient {exc.item_id}: need {exc.required}, have {exc.available}.\n"
                    f"MEANS: State unchanged. Effect requires more items than available.\n"
                    f"DO: Acquire more {exc.item_id} before retrying."
                ),
                context={
                    "item_id": exc.item_id,
                    "item_name": exc.item_id,
                    "required": exc.required,
                    "available": exc.available,
                },
            )
        if isinstance(exc, InvalidLocation):
            return GameError(
                kind=ErrorKind.INVALID_LOCATION,
                effect=Effect.NONE,
                recovery=Recovery.CORRECTABLE,
                detail=(
                    f"WHAT: Location {exc.location_id} is not valid.\n"
                    f"MEANS: State unchanged.\n"
                    f"DO: Check available locations via GET /v1/world/places."
                ),
                context={"location_id": exc.location_id},
            )
        if isinstance(exc, SceneNotAvailable):
            return GameError(
                kind=ErrorKind.SCENE_NOT_AVAILABLE,
                effect=Effect.NONE,
                recovery=Recovery.RETRYABLE,
                detail=(
                    f"WHAT: No scene available for session {exc.session_id}.\n"
                    f"MEANS: State unchanged. Scene selection found no candidates.\n"
                    f"DO: Retry the request. If it persists, check content configuration."
                ),
                context={"session_id": exc.session_id},
            )
        return self._engine_error("unknown", exc)

    @staticmethod
    def _engine_error(session_id: str, exc: Exception) -> GameError:
        return GameError(
            kind=ErrorKind.ENGINE_FAILURE,
            effect=Effect.UNKNOWN,
            recovery=Recovery.ESCALATE,
            detail=(
                f"WHAT: Unexpected engine error for session {session_id}: {exc!r}.\n"
                f"MEANS: Cannot determine state impact. Session may be inconsistent.\n"
                f"DO: Report this to a developer. Do not retry without investigation."
            ),
            context={"session_id": session_id, "error": str(exc)},
        )

    @staticmethod
    def _match_intent(text: str, choices: list[dict]) -> str | None:
        """Match free-text input against choice labels."""
        text_lower = text.lower()
        for choice in choices:
            label = choice.get("label", "").lower()
            if label and label in text_lower:
                return choice.get("action_id") or choice.get("choice_id")
        return None
