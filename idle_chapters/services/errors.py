"""Structured error model for Idle Chapters.

Profiles RFC 9457 (Problem Details for HTTP APIs) with extension members
for state semantics (effect), recovery guidance, and ANSI Z535 signal
word severity classification.

Projections transform a GameError for different audiences:
- player: minimal RFC 9457 (type, title, status)
- developer: full RFC 9457 + Z535 extensions
- agent (future): RFC 9457 + extensions, no prose detail
"""

from __future__ import annotations

import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4


class ErrorKind(StrEnum):
    SESSION_NOT_FOUND = "session_not_found"
    ACTION_NOT_ELIGIBLE = "action_not_eligible"
    INTENT_NO_MATCH = "intent_no_match"
    INSUFFICIENT_INVENTORY = "insufficient_inventory"
    INVALID_LOCATION = "invalid_location"
    SCENE_NOT_AVAILABLE = "scene_not_available"
    ENGINE_FAILURE = "engine_failure"
    PERSISTENCE_FAILURE = "persistence_failure"
    JOURNAL_PAGE_NOT_FOUND = "journal_page_not_found"


class Effect(StrEnum):
    NONE = "none"
    APPLIED = "applied"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class Recovery(StrEnum):
    RETRYABLE = "retryable"
    CORRECTABLE = "correctable"
    TERMINAL = "terminal"
    ESCALATE = "escalate"


class Signal(StrEnum):
    """ANSI Z535 signal word hierarchy, adapted for software state severity."""
    DANGER = "DANGER"
    WARNING = "WARNING"
    CAUTION = "CAUTION"
    NOTICE = "NOTICE"


_HTTP_STATUS: dict[ErrorKind, int] = {
    ErrorKind.SESSION_NOT_FOUND: 404,
    ErrorKind.ACTION_NOT_ELIGIBLE: 409,
    ErrorKind.INTENT_NO_MATCH: 422,
    ErrorKind.INSUFFICIENT_INVENTORY: 409,
    ErrorKind.INVALID_LOCATION: 422,
    ErrorKind.SCENE_NOT_AVAILABLE: 503,
    ErrorKind.ENGINE_FAILURE: 500,
    ErrorKind.PERSISTENCE_FAILURE: 503,
    ErrorKind.JOURNAL_PAGE_NOT_FOUND: 404,
}

_TITLES: dict[ErrorKind, str] = {
    ErrorKind.SESSION_NOT_FOUND: "Session Not Found",
    ErrorKind.ACTION_NOT_ELIGIBLE: "Action Not Eligible",
    ErrorKind.INTENT_NO_MATCH: "Intent No Match",
    ErrorKind.INSUFFICIENT_INVENTORY: "Insufficient Inventory",
    ErrorKind.INVALID_LOCATION: "Invalid Location",
    ErrorKind.SCENE_NOT_AVAILABLE: "Scene Not Available",
    ErrorKind.ENGINE_FAILURE: "Engine Failure",
    ErrorKind.PERSISTENCE_FAILURE: "Persistence Failure",
    ErrorKind.JOURNAL_PAGE_NOT_FOUND: "Journal Page Not Found",
}

_URN_PREFIX = "urn:idle-chapters:error:"
_INSTANCE_PREFIX = "urn:idle-chapters:occurrence:"


def _derive_signal(effect: Effect, recovery: Recovery) -> Signal:
    """Derive Z535 signal word from effect + recovery.

    Exhaustive mapping per design doc signal derivation table.
    Effect determines the floor; recovery can raise it.
    """
    if effect == Effect.UNKNOWN:
        return Signal.DANGER
    if effect == Effect.PARTIAL:
        if recovery == Recovery.ESCALATE:
            return Signal.DANGER
        return Signal.WARNING
    if effect == Effect.APPLIED:
        if recovery == Recovery.ESCALATE:
            return Signal.WARNING
        if recovery == Recovery.TERMINAL:
            return Signal.NOTICE
        return Signal.CAUTION
    # effect == NONE
    if recovery == Recovery.TERMINAL:
        return Signal.NOTICE
    return Signal.CAUTION


def _find_repo_root() -> Path:
    """Walk up from this file to find the repository root (.git directory)."""
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".git").is_dir():
            return parent
    return path.parents[3]


@lru_cache(maxsize=1)
def _load_templates() -> dict[str, dict[str, str]]:
    path = _find_repo_root() / "assets" / "error_templates.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


class GameError(Exception):
    def __init__(
        self,
        kind: ErrorKind,
        effect: Effect,
        recovery: Recovery,
        detail: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        self.kind = kind
        self.effect = effect
        self.recovery = recovery
        self.detail = detail
        self.context = context or {}
        super().__init__(detail or str(kind))

    @property
    def http_status(self) -> int:
        return _HTTP_STATUS.get(self.kind, 500)

    @property
    def signal(self) -> Signal:
        return _derive_signal(self.effect, self.recovery)

    @property
    def type_uri(self) -> str:
        return f"{_URN_PREFIX}{self.kind.value}"

    @property
    def title(self) -> str:
        return _TITLES.get(self.kind, str(self.kind))

    def project_player(self) -> dict[str, Any]:
        """Minimal RFC 9457: type, title (rendered template), status."""
        templates = _load_templates()
        entry = templates.get(self.kind.value, {})
        template = entry.get("template", "")
        fallback = entry.get("fallback", "Something unexpected happened.")
        try:
            message = template.format(**self.context) if template else fallback
        except (KeyError, IndexError):
            message = fallback
        return {
            "type": self.type_uri,
            "title": message,
            "status": self.http_status,
        }

    def project_developer(self) -> dict[str, Any]:
        """Full RFC 9457 + Z535 extensions."""
        return {
            "type": self.type_uri,
            "title": self.title,
            "status": self.http_status,
            "detail": self.detail,
            "instance": f"{_INSTANCE_PREFIX}{uuid4()}",
            "effect": self.effect.value,
            "recovery": self.recovery.value,
            "signal": self.signal.value,
            "context": self.context,
        }
