"""Typed domain exceptions for Idle Chapters.

Each exception carries structured data relevant to the failure.
These are domain vocabulary -- they know nothing about HTTP, projections,
or the GameError model. The service layer translates them.
"""

from __future__ import annotations


class SessionNotFound(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class ActionNotEligible(Exception):
    def __init__(
        self,
        action_id: str,
        session_id: str,
        unmet_conditions: list[str] | None = None,
    ) -> None:
        self.action_id = action_id
        self.session_id = session_id
        self.unmet_conditions = unmet_conditions or []
        super().__init__(
            f"Action {action_id} not eligible for session {session_id}"
        )


class IntentNoMatch(Exception):
    def __init__(
        self,
        input_text: str,
        available_actions: list[str] | None = None,
    ) -> None:
        self.input_text = input_text
        self.available_actions = available_actions or []
        super().__init__(f"No action matched intent: {input_text!r}")


class InsufficientInventory(Exception):
    def __init__(self, item_id: str, required: int, available: int) -> None:
        self.item_id = item_id
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient {item_id}: need {required}, have {available}"
        )


class InvalidLocation(Exception):
    def __init__(self, location_id: str) -> None:
        self.location_id = location_id
        super().__init__(f"Invalid location: {location_id}")


class SceneNotAvailable(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"No scene available for session {session_id}")
