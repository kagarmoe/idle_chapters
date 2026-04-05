# Structured Error Model Implementation Plan (Phase A: Sessions)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace ValueError/HTTPException error handling in session endpoints with a three-layer structured error model (typed domain exceptions, GameError, audience projections).

**Architecture:** Domain raises typed exceptions carrying domain data. Service layer catches them and constructs a GameError (kind/effect/recovery/detail/context). API router catches GameError, selects projection (player/developer) via Accept-Projection header, and returns the appropriate response shape.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2.12, jsonschema, pytest

**Design doc:** `design-docs/plans/2026-04-04-structured-errors-design.md`

**Tone contract:** `design-docs/game_design/tone_contract.md` (all player-facing templates MUST comply)

---

### Task 1: Domain Exception Classes

**Files:**
- Create: `apps/api/app/domain/errors.py`
- Test: `apps/api/tests/test_domain_errors.py`

**Step 1: Write the failing tests**

```python
# apps/api/tests/test_domain_errors.py
import pytest

from app.domain.errors import (
    SessionNotFound,
    ActionNotEligible,
    IntentNoMatch,
    InsufficientInventory,
    InvalidLocation,
    SceneNotAvailable,
)


def test_session_not_found_carries_session_id():
    err = SessionNotFound(session_id="abc-123")
    assert err.session_id == "abc-123"
    assert "abc-123" in str(err)


def test_action_not_eligible_carries_context():
    err = ActionNotEligible(
        action_id="gather_herbs",
        session_id="abc-123",
        unmet_conditions=["flags_set: visited_garden"],
    )
    assert err.action_id == "gather_herbs"
    assert err.session_id == "abc-123"
    assert err.unmet_conditions == ["flags_set: visited_garden"]


def test_intent_no_match_carries_input_and_actions():
    err = IntentNoMatch(
        input_text="dance around",
        available_actions=["brew tea", "rest"],
    )
    assert err.input_text == "dance around"
    assert err.available_actions == ["brew tea", "rest"]


def test_insufficient_inventory_carries_amounts():
    err = InsufficientInventory(
        item_id="chamomile",
        required=3,
        available=1,
    )
    assert err.item_id == "chamomile"
    assert err.required == 3
    assert err.available == 1


def test_invalid_location_carries_location_id():
    err = InvalidLocation(location_id="nowhere")
    assert err.location_id == "nowhere"


def test_scene_not_available_carries_session_id():
    err = SceneNotAvailable(session_id="abc-123")
    assert err.session_id == "abc-123"


def test_all_exceptions_are_exceptions():
    """Every domain error must be a subclass of Exception."""
    for cls in [
        SessionNotFound,
        ActionNotEligible,
        IntentNoMatch,
        InsufficientInventory,
        InvalidLocation,
        SceneNotAvailable,
    ]:
        assert issubclass(cls, Exception)
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m pytest tests/test_domain_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.domain.errors'`

**Step 3: Write minimal implementation**

```python
# apps/api/app/domain/errors.py
"""Typed domain exceptions for Idle Chapters.

Each exception carries structured data relevant to the failure.
These are domain vocabulary — they know nothing about HTTP, projections,
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
```

**Step 4: Run tests to verify they pass**

Run: `cd apps/api && python -m pytest tests/test_domain_errors.py -v`
Expected: 7 passed

**Step 5: Commit**

```bash
git add apps/api/app/domain/errors.py apps/api/tests/test_domain_errors.py
git commit -m "feat: add typed domain exception classes"
```

---

### Task 2: GameError Model and Projection Logic

**Files:**
- Create: `apps/api/app/services/errors.py`
- Test: `apps/api/tests/test_game_error.py`

**Step 1: Write the failing tests**

```python
# apps/api/tests/test_game_error.py
import pytest

from app.services.errors import GameError, ErrorKind, Effect, Recovery


class TestGameErrorConstruction:
    def test_create_game_error_with_all_fields(self):
        err = GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
            detail="WHAT: No session.\nMEANS: Nothing modified.\nDO: Create new.",
            context={"session_id": "abc-123"},
        )
        assert err.kind == ErrorKind.SESSION_NOT_FOUND
        assert err.effect == Effect.NONE
        assert err.recovery == Recovery.TERMINAL
        assert err.context["session_id"] == "abc-123"

    def test_game_error_is_exception(self):
        err = GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
        )
        assert isinstance(err, Exception)

    def test_http_status_mapping(self):
        assert GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
        ).http_status == 404

        assert GameError(
            kind=ErrorKind.ACTION_NOT_ELIGIBLE,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
        ).http_status == 409

        assert GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
        ).http_status == 422

        assert GameError(
            kind=ErrorKind.ENGINE_FAILURE,
            effect=Effect.UNKNOWN,
            recovery=Recovery.ESCALATE,
        ).http_status == 500

        assert GameError(
            kind=ErrorKind.PERSISTENCE_FAILURE,
            effect=Effect.PARTIAL,
            recovery=Recovery.RETRYABLE,
        ).http_status == 503


class TestPlayerProjection:
    def test_renders_template_with_context(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={"input": "dance", "available_actions": "brew tea, rest"},
        )
        projection = err.project_player()
        assert projection["kind"] == "intent_no_match"
        assert "dance" in projection["message"]
        assert "brew tea, rest" in projection["message"]

    def test_falls_back_when_placeholder_missing(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={},  # missing placeholders
        )
        projection = err.project_player()
        assert "kind" in projection
        assert "message" in projection
        # Should use fallback, not crash
        assert len(projection["message"]) > 0


class TestDeveloperProjection:
    def test_includes_all_structured_fields(self):
        err = GameError(
            kind=ErrorKind.PERSISTENCE_FAILURE,
            effect=Effect.PARTIAL,
            recovery=Recovery.RETRYABLE,
            detail="WHAT: Write failed.\nMEANS: State diverged.\nDO: Retry.",
            context={"session_id": "abc-123"},
        )
        projection = err.project_developer()
        assert projection["kind"] == "persistence_failure"
        assert projection["effect"] == "partial"
        assert projection["recovery"] == "retryable"
        assert "WHAT" in projection["detail"]
        assert projection["context"]["session_id"] == "abc-123"
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m pytest tests/test_game_error.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.errors'`

**Step 3: Write minimal implementation**

```python
# apps/api/app/services/errors.py
"""Structured error model for Idle Chapters.

GameError is the single source of truth for all errors in the system.
It carries classification (kind), state impact (effect), recovery
guidance (recovery), developer detail (Z535), and machine context.

Projections transform a GameError for different audiences:
- player: tone-contract-compliant template string
- developer: full structured detail (Z535: WHAT/MEANS/DO)
- agent (future): kind + effect + recovery + context only
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any


class ErrorKind(StrEnum):
    SESSION_NOT_FOUND = "session_not_found"
    ACTION_NOT_ELIGIBLE = "action_not_eligible"
    INTENT_NO_MATCH = "intent_no_match"
    INSUFFICIENT_INVENTORY = "insufficient_inventory"
    INVALID_LOCATION = "invalid_location"
    SCENE_NOT_AVAILABLE = "scene_not_available"
    ENGINE_FAILURE = "engine_failure"
    PERSISTENCE_FAILURE = "persistence_failure"


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


_HTTP_STATUS: dict[ErrorKind, int] = {
    ErrorKind.SESSION_NOT_FOUND: 404,
    ErrorKind.ACTION_NOT_ELIGIBLE: 409,
    ErrorKind.INTENT_NO_MATCH: 422,
    ErrorKind.INSUFFICIENT_INVENTORY: 409,
    ErrorKind.INVALID_LOCATION: 422,
    ErrorKind.SCENE_NOT_AVAILABLE: 503,
    ErrorKind.ENGINE_FAILURE: 500,
    ErrorKind.PERSISTENCE_FAILURE: 503,
}

# Loaded once on first use; module-level cache.
_templates: dict[str, dict[str, str]] | None = None


def _load_templates() -> dict[str, dict[str, str]]:
    global _templates
    if _templates is not None:
        return _templates
    path = Path(__file__).resolve().parents[3] / "assets" / "error_templates.json"
    if path.exists():
        _templates = json.loads(path.read_text(encoding="utf-8"))
    else:
        _templates = {}
    return _templates


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

    def project_player(self) -> dict[str, str]:
        templates = _load_templates()
        entry = templates.get(self.kind.value, {})
        template = entry.get("template", "")
        fallback = entry.get("fallback", "Something unexpected happened.")
        try:
            message = template.format(**self.context) if template else fallback
        except (KeyError, IndexError):
            message = fallback
        return {"kind": self.kind.value, "message": message}

    def project_developer(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "effect": self.effect.value,
            "recovery": self.recovery.value,
            "detail": self.detail,
            "context": self.context,
        }
```

**Step 4: Run tests to verify they pass**

Run: `cd apps/api && python -m pytest tests/test_game_error.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
git add apps/api/app/services/errors.py apps/api/tests/test_game_error.py
git commit -m "feat: add GameError model with projection logic"
```

---

### Task 3: Error Templates and Schema

**Files:**
- Create: `assets/error_templates.json`
- Create: `schemas/error_templates.schema.json`
- Test: `apps/api/tests/test_error_templates.py`

**Step 1: Write the failing tests**

```python
# apps/api/tests/test_error_templates.py
import json
from pathlib import Path

import pytest
from jsonschema import validate

from app.services.errors import ErrorKind


@pytest.fixture(scope="module")
def repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "CLAUDE.md").exists():
            return parent
    return path.parents[4]


@pytest.fixture(scope="module")
def templates(repo_root: Path) -> dict:
    path = repo_root / "assets" / "error_templates.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema(repo_root: Path) -> dict:
    path = repo_root / "schemas" / "error_templates.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_templates_validate_against_schema(templates, schema):
    validate(instance=templates, schema=schema)


def test_every_error_kind_has_a_template(templates):
    for kind in ErrorKind:
        assert kind.value in templates, f"Missing template for {kind.value}"


def test_every_template_has_required_keys(templates):
    for kind, entry in templates.items():
        assert "template" in entry, f"{kind} missing 'template'"
        assert "fallback" in entry, f"{kind} missing 'fallback'"


# --- Tone contract compliance ---
# These words violate design-docs/game_design/tone_contract.md:
# fear, threat, danger, urgent, must, fail, lose, lost, lack,
# scarcity, shortage, blame, fault, risk, deadline, rush

DISALLOWED_WORDS = [
    "fear", "threat", "danger", "urgent", "must", "fail",
    "lose", "lost", "lack", "scarcity", "shortage", "blame",
    "fault", "risk", "deadline", "rush", "destroyed", "broken",
    "terrible", "horrible", "wrong", "error", "crash", "panic",
]


def test_player_templates_comply_with_tone_contract(templates):
    violations = []
    for kind, entry in templates.items():
        for field in ("template", "fallback"):
            text = entry.get(field, "").lower()
            for word in DISALLOWED_WORDS:
                if word in text:
                    violations.append(f"{kind}.{field} contains '{word}'")
    assert violations == [], f"Tone contract violations:\n" + "\n".join(violations)
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m pytest tests/test_error_templates.py -v`
Expected: FAIL (files don't exist yet)

**Step 3: Create the schema**

```json
// schemas/error_templates.schema.json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Error Templates",
    "description": "Player-facing error message templates. All text must comply with the tone contract.",
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["template", "fallback"],
        "properties": {
            "template": {
                "type": "string",
                "description": "Message template with {placeholder} substitution from GameError.context"
            },
            "fallback": {
                "type": "string",
                "description": "Used when template placeholders cannot be filled"
            }
        },
        "additionalProperties": false
    }
}
```

**Step 4: Create the templates**

```json
// assets/error_templates.json
{
    "session_not_found": {
        "template": "That story has found its own ending. You're welcome to begin a new one whenever you'd like.",
        "fallback": "It looks like it's time for a fresh start. A new story is waiting."
    },
    "action_not_eligible": {
        "template": "That doesn't seem possible right now. Maybe explore a bit more first.",
        "fallback": "That doesn't seem to be an option at the moment."
    },
    "intent_no_match": {
        "template": "Hmm, I'm not sure what you mean by \"{input}\". These are the things you could do here: {available_actions}.",
        "fallback": "I didn't quite catch that. What would you like to do?"
    },
    "insufficient_inventory": {
        "template": "You have {available} {item_name} with you. This would take {required}. Maybe you'll find more while exploring.",
        "fallback": "You don't quite have what you'd need for that yet."
    },
    "invalid_location": {
        "template": "That place doesn't seem to be nearby. Perhaps somewhere else calls to you.",
        "fallback": "That doesn't seem to be a place you can visit right now."
    },
    "scene_not_available": {
        "template": "This place is quietly resting for the moment. Perhaps come back a little later.",
        "fallback": "Nothing seems to be happening here right now. That's alright."
    },
    "engine_failure": {
        "template": "Something got a little tangled. Perhaps try again in a moment.",
        "fallback": "Something got a little tangled. Perhaps try again in a moment."
    },
    "persistence_failure": {
        "template": "Your story was briefly interrupted. Try that again and it should settle.",
        "fallback": "Something got a little tangled. Perhaps try again in a moment."
    }
}
```

**Step 5: Run tests to verify they pass**

Run: `cd apps/api && python -m pytest tests/test_error_templates.py -v`
Expected: 4 passed

**Step 6: Commit**

```bash
git add assets/error_templates.json schemas/error_templates.schema.json apps/api/tests/test_error_templates.py
git commit -m "feat: add error templates and schema with tone contract tests"
```

---

### Task 4: Wire Domain Exceptions into Engine, Effects, and Selector

**Files:**
- Modify: `apps/api/app/domain/effects.py` (line 22: `ValueError` -> `InsufficientInventory`)
- Modify: `apps/api/app/domain/engine.py` (lines 33, 86, 95: `ValueError` -> typed exceptions)
- Modify: `apps/api/app/domain/selector.py` (line 41: `ValueError` -> `SceneNotAvailable`)
- Modify: `apps/api/app/domain/scene_generator.py` (line 65: `ValueError` -> `InvalidLocation`)
- Modify: `apps/api/tests/test_effects.py` (line 40: update expected exception)

**Step 1: Update the effects test**

Change `apps/api/tests/test_effects.py` line 40 from:

```python
    with pytest.raises(ValueError):
        apply_effects(state, effects)
```

to:

```python
    from app.domain.errors import InsufficientInventory

    with pytest.raises(InsufficientInventory) as exc_info:
        apply_effects(state, effects)
    assert exc_info.value.item_id == "item_1"
    assert exc_info.value.required == 1
    assert exc_info.value.available == 0
```

**Step 2: Run test to verify it fails**

Run: `cd apps/api && python -m pytest tests/test_effects.py::test_apply_effects_prevents_negative_inventory -v`
Expected: FAIL with `Failed: DID NOT RAISE <class 'app.domain.errors.InsufficientInventory'>`

**Step 3: Update effects.py**

In `apps/api/app/domain/effects.py`, add import at top:

```python
from app.domain.errors import InsufficientInventory
```

Replace line 22-24:

```python
        if current < qty:
            raise ValueError(
                f"Cannot remove {qty} of '{item}': only {current} in inventory"
            )
```

with:

```python
        if current < qty:
            raise InsufficientInventory(
                item_id=item, required=qty, available=current,
            )
```

**Step 4: Run test to verify it passes**

Run: `cd apps/api && python -m pytest tests/test_effects.py -v`
Expected: 2 passed

**Step 5: Update engine.py**

In `apps/api/app/domain/engine.py`, add import at top:

```python
from app.domain.errors import ActionNotEligible, SessionNotFound
```

Replace line 33:

```python
            raise ValueError(f"Unknown command: {command}")
```

with:

```python
            raise ValueError(f"Unknown command: {command}")  # keep as ValueError — not a domain error
```

No change here — `Unknown command` is a programming error, not a domain error. The engine's `ValueError` for unknown commands stays as-is.

Replace lines 85-86 in `_handle_choose`:

```python
        if not choice_id:
            raise ValueError("choice_id required for 'choose option' command")
```

with:

```python
        if not choice_id:
            raise ActionNotEligible(
                action_id="(none)",
                session_id=state.session_id,
                unmet_conditions=["choice_id is required"],
            )
```

Replace line 95:

```python
            raise ValueError(f"Unknown action: {choice_id}")
```

with:

```python
            raise ActionNotEligible(
                action_id=choice_id,
                session_id=state.session_id,
                unmet_conditions=["action not found in current scene"],
            )
```

**Step 6: Update selector.py**

In `apps/api/app/domain/selector.py`, add import at top:

```python
from app.domain.errors import SceneNotAvailable
```

Replace line 41:

```python
        raise ValueError("No eligible scenes")
```

with:

```python
        raise SceneNotAvailable(session_id="")  # session_id unavailable at selector level
```

Note: The selector doesn't have access to session_id. The service layer's `except Exception` catch will wrap this into a proper GameError with the correct session_id via `_engine_error`. Alternatively, the service layer can catch `SceneNotAvailable` specifically — which it already does in `perform_action`. For the `enter` flow, add `SceneNotAvailable` to the exception handling:

In `apps/api/app/domain/engine.py` `_handle_enter`, the `choose_scene` call can raise `SceneNotAvailable`. Since this happens inside `engine.step`, the service layer's `except Exception` in `enter()` will catch it and map it to `engine_failure`. To get the correct mapping, update the `enter` method in the service (Task 5) to also catch domain exceptions — see Task 5.

**Step 7: Update scene_generator.py**

In `apps/api/app/domain/scene_generator.py`, add import at top:

```python
from app.domain.errors import InvalidLocation
```

Replace line 65:

```python
        raise ValueError(f"Unknown place_id: {state.current_place_id}")
```

with:

```python
        raise InvalidLocation(location_id=state.current_place_id)
```

**Step 8: Run full engine, effects, and scene generation tests**

Run: `cd apps/api && python -m pytest tests/test_engine.py tests/test_effects.py tests/test_scene_generation.py -v`
Expected: all pass

**Step 9: Commit**

```bash
git add apps/api/app/domain/effects.py apps/api/app/domain/engine.py apps/api/app/domain/selector.py apps/api/app/domain/scene_generator.py apps/api/tests/test_effects.py
git commit -m "refactor: replace ValueError with typed domain exceptions in engine, effects, selector, and generator"
```

---

### Task 5: Wire GameError into Session Service

**Files:**
- Modify: `apps/api/app/services/session_service.py`
- Test: `apps/api/tests/test_game_error_mapping.py`

**Step 1: Write the failing tests**

```python
# apps/api/tests/test_game_error_mapping.py
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.domain.engine import Engine
from app.domain.errors import (
    ActionNotEligible,
    InsufficientInventory,
    IntentNoMatch,
    SessionNotFound,
)
from app.domain.state import PlayerState
from app.services.errors import Effect, ErrorKind, GameError, Recovery
from app.services.session_service import SessionService


def _make_service(state=None, engine=None):
    state_store = MagicMock()
    state_store.get_state.return_value = state
    journal_store = MagicMock()
    event_store = MagicMock()
    repo = SimpleNamespace(
        places_by_id={},
        scenes_by_place_id={},
        actions_by_id={},
        journal_templates_by_entry_type={},
        journal_templates_by_id={},
        lexicon_by_key={},
        collectibles_by_id={},
        ingredient_substitutions_by_token={},
    )
    return SessionService(
        repo=repo,
        engine=engine or Engine(),
        state_store=state_store,
        journal_store=journal_store,
        event_store=event_store,
    )


def test_session_not_found_maps_to_game_error():
    service = _make_service(state=None)
    with pytest.raises(GameError) as exc_info:
        service.perform_action("missing-id", "some_action")
    err = exc_info.value
    assert err.kind == ErrorKind.SESSION_NOT_FOUND
    assert err.effect == Effect.NONE
    assert err.recovery == Recovery.TERMINAL
    assert err.context["session_id"] == "missing-id"
    assert "WHAT" in err.detail
    assert "MEANS" in err.detail
    assert "DO" in err.detail


def test_action_not_eligible_maps_to_game_error():
    state = PlayerState(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
    )
    service = _make_service(state=state)
    with pytest.raises(GameError) as exc_info:
        service.perform_action("s1", "nonexistent_action")
    err = exc_info.value
    assert err.kind == ErrorKind.ACTION_NOT_ELIGIBLE
    assert err.effect == Effect.NONE
    assert err.recovery == Recovery.CORRECTABLE


def test_intent_no_match_maps_to_game_error():
    state = PlayerState(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
    )
    service = _make_service(state=state)
    with pytest.raises(GameError) as exc_info:
        service.submit_intent("s1", "fly to the moon")
    err = exc_info.value
    assert err.kind == ErrorKind.INTENT_NO_MATCH
    assert err.effect == Effect.NONE
    assert err.recovery == Recovery.CORRECTABLE
    assert err.context["input"] == "fly to the moon"


def test_persistence_failure_maps_to_partial_effect():
    state = PlayerState(
        session_id="s1",
        current_place_id="cottage_home",
        inventory={},
        flags=set(),
    )
    engine = MagicMock()
    engine.step.return_value = MagicMock(
        journal_page=None, new_state=state, debug={}, choices=[],
    )
    service = _make_service(state=state, engine=engine)
    service._state_store.upsert_state.side_effect = Exception("DB down")
    with pytest.raises(GameError) as exc_info:
        service.enter("s1")
    err = exc_info.value
    assert err.kind == ErrorKind.PERSISTENCE_FAILURE
    assert err.effect == Effect.PARTIAL
    assert err.recovery == Recovery.RETRYABLE
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m pytest tests/test_game_error_mapping.py -v`
Expected: FAIL (service still raises ValueError, not GameError)

**Step 3: Rewrite session_service.py**

Replace the full contents of `apps/api/app/services/session_service.py`:

```python
from __future__ import annotations

import logging
from uuid import uuid4

from app.domain.engine import Engine
from app.domain.errors import (
    ActionNotEligible,
    InsufficientInventory,
    IntentNoMatch,
    InvalidLocation,
    SceneNotAvailable,
    SessionNotFound,
)
from app.domain.state import PlayerState
from app.domain.step_result import StepResult
from app.services.errors import Effect, ErrorKind, GameError, Recovery

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
            # For new sessions, no prior state exists to diverge from.
            # For existing sessions, state was computed but not saved.
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
                    "item_name": exc.item_id,  # derived from item_id; template uses {item_name} for player-friendly display
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
        # Fallback: treat as engine failure
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
```

**Step 4: Run tests to verify they pass**

Run: `cd apps/api && python -m pytest tests/test_game_error_mapping.py -v`
Expected: 4 passed

**Step 5: Run existing tests to check nothing broke**

Run: `cd apps/api && python -m pytest tests/ -v --ignore=tests/test_persistence.py`
Expected: all pass. Some tests that expect `ValueError` from the service layer may now get `GameError` — fix them in this step if needed.

**Step 6: Commit**

```bash
git add apps/api/app/services/session_service.py apps/api/tests/test_game_error_mapping.py
git commit -m "feat: wire GameError into session service with Z535 detail"
```

---

### Task 6: API Router Error Handling and Projection

**Files:**
- Modify: `apps/api/app/api/routers/sessions.py`
- Modify: `apps/api/app/api/models.py`
- Create: `schemas/error_response.schema.json`
- Test: `apps/api/tests/test_error_projections.py`

**Step 1: Write the failing tests**

```python
# apps/api/tests/test_error_projections.py
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app


@pytest.fixture(scope="module")
def repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "CLAUDE.md").exists():
            return parent
    return path.parents[4]


@pytest.fixture(scope="module")
def client(repo_root) -> TestClient:
    app = create_app()
    return TestClient(app)


class TestPlayerProjection:
    def test_session_not_found_returns_player_message(self, client):
        resp = client.get("/v1/sessions/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert body["error"]["kind"] == "session_not_found"
        assert "message" in body["error"]
        # Must not contain developer detail
        assert "WHAT" not in body["error"].get("detail", "")

    def test_default_projection_is_player(self, client):
        resp = client.get("/v1/sessions/nonexistent")
        body = resp.json()
        # Player projection: kind + message only
        assert set(body["error"].keys()) == {"kind", "message"}


class TestDeveloperProjection:
    def test_session_not_found_returns_structured_detail(self, client):
        resp = client.get(
            "/v1/sessions/nonexistent",
            headers={"Accept-Projection": "developer"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        err = body["error"]
        assert err["kind"] == "session_not_found"
        assert err["effect"] == "none"
        assert err["recovery"] == "terminal"
        assert "WHAT" in err["detail"]
        assert "MEANS" in err["detail"]
        assert "DO" in err["detail"]
        assert "session_id" in err["context"]
```

**Step 2: Run tests to verify they fail**

Run: `cd apps/api && python -m pytest tests/test_error_projections.py -v`
Expected: FAIL (router still returns old `{"detail": "..."}` format)

**Step 3: Add Pydantic error response models**

Add to `apps/api/app/api/models.py`:

```python
class PlayerErrorBody(BaseModel):
    kind: str
    message: str


class DeveloperErrorBody(BaseModel):
    kind: str
    effect: str
    recovery: str
    detail: str
    context: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: PlayerErrorBody | DeveloperErrorBody
```

**Step 4: Update sessions router**

Replace `apps/api/app/api/routers/sessions.py` with GameError handling. The key change: instead of `except ValueError as e: raise HTTPException(...)`, use a FastAPI exception handler.

Add a `game_error_handler` in `apps/api/app/api/app.py` (or wherever `create_app` lives):

First, read `apps/api/app/api/app.py` to see the app factory.

Then add after app creation:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from app.services.errors import GameError


@app.exception_handler(GameError)
async def handle_game_error(request: Request, exc: GameError) -> JSONResponse:
    projection = request.headers.get("Accept-Projection", "player")
    if projection == "developer":
        body = {"error": exc.project_developer()}
    else:
        body = {"error": exc.project_player()}
    return JSONResponse(status_code=exc.http_status, content=body)
```

Then simplify `sessions.py` — remove all `try/except ValueError` blocks. Let `GameError` propagate to the exception handler. Replace the full router file:

```python
# apps/api/app/api/routers/sessions.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_session_service
from app.api.models import (
    ActionRequest,
    IntentRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionGetResponse,
    StepResponse,
    ViewAction,
    ViewModel,
)
from app.domain.step_result import StepResult
from app.services.errors import Effect, ErrorKind, GameError, Recovery
from app.services.session_service import SessionService

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


def _view_from_result(result: StepResult) -> ViewModel:
    """Build a ViewModel from a StepResult."""
    prompt = None
    if result.journal_page:
        prompt = result.journal_page.get("body") or result.journal_page.get("prompt")

    return ViewModel(
        prompt=prompt,
        scene_id=result.debug.get("selected_scene_id") if result.debug else None,
        eligible_actions=[
            ViewAction(
                action_id=c.get("action_id") or c.get("choice_id", ""),
                label=c.get("label", c.get("action_id") or c.get("choice_id", "")),
            )
            for c in result.choices
        ],
    )


def _step_response(result: StepResult) -> StepResponse:
    """Build a StepResponse from a StepResult."""
    view = _view_from_result(result)
    return StepResponse(
        view=view,
        journal_page=result.journal_page,
        choices=view.eligible_actions,
    )


@router.post("", response_model=SessionCreateResponse)
def create_session(
    request: SessionCreateRequest = None,
    service: SessionService = Depends(get_session_service),
) -> SessionCreateResponse:
    place_id = request.place_id if request else "cottage_home"
    session_id, result = service.create_session(place_id=place_id)
    view = _view_from_result(result)
    return SessionCreateResponse(
        session_id=session_id,
        view=view,
        journal_page=result.journal_page,
    )


@router.get("/{session_id}", response_model=SessionGetResponse)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionGetResponse:
    state = service.get_session(session_id)
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
    return SessionGetResponse(
        session_id=session_id,
        view=ViewModel(),
        state={
            "current_place_id": state.current_place_id,
            "inventory": state.inventory,
            "flags": sorted(state.flags),
            "time_tick": state.time_tick,
        },
    )


@router.post("/{session_id}/enter", response_model=StepResponse)
def enter_place(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    result = service.enter(session_id)
    return _step_response(result)


@router.post("/{session_id}/action", response_model=StepResponse)
def submit_action(
    session_id: str,
    request: ActionRequest,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    result = service.perform_action(session_id, request.action_id)
    return _step_response(result)


@router.post("/{session_id}/intent", response_model=StepResponse)
def submit_intent(
    session_id: str,
    request: IntentRequest,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    result = service.submit_intent(session_id, request.input)
    return _step_response(result)


@router.get("/{session_id}/journal")
def list_journal_pages(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> list[dict]:
    state = service.get_session(session_id)
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
    return service._journal_store.list_pages(session_id)


@router.get("/{session_id}/journal/{page_id}")
def get_journal_page(
    session_id: str,
    page_id: str,
    service: SessionService = Depends(get_session_service),
) -> dict:
    state = service.get_session(session_id)
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
    page = service._journal_store.get_page(session_id, page_id)
    if page is None:
        raise GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
            detail=(
                f"WHAT: Journal page {page_id} not found for session {session_id}.\n"
                f"MEANS: Nothing was modified.\n"
                f"DO: List pages via GET /v1/sessions/{session_id}/journal."
            ),
            context={"session_id": session_id, "page_id": page_id},
        )
    return page
```

**Step 5: Create error response schema**

```json
// schemas/error_response.schema.json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Error Response",
    "description": "API error response envelope. Shape varies by Accept-Projection header.",
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["kind"],
            "properties": {
                "kind": { "type": "string" },
                "message": { "type": "string" },
                "effect": { "type": "string", "enum": ["none", "applied", "partial", "unknown"] },
                "recovery": { "type": "string", "enum": ["retryable", "correctable", "terminal", "escalate"] },
                "detail": { "type": "string" },
                "context": { "type": "object" }
            }
        }
    },
    "additionalProperties": false
}
```

**Step 6: Run tests to verify they pass**

Run: `cd apps/api && python -m pytest tests/test_error_projections.py -v`
Expected: 3 passed

**Step 7: Run full test suite**

Run: `cd apps/api && python -m pytest tests/ -v --ignore=tests/test_persistence.py`
Expected: all pass

**Step 8: Commit**

```bash
git add apps/api/app/api/app.py apps/api/app/api/routers/sessions.py apps/api/app/api/models.py schemas/error_response.schema.json apps/api/tests/test_error_projections.py
git commit -m "feat: add GameError exception handler with Accept-Projection support"
```

---

### Task 7: Update Frontend API Client

**Files:**
- Modify: `apps/web/src/lib/api.ts`

**Step 1: Add structured error types**

Add to `apps/web/src/lib/api.ts` after the existing interfaces:

```typescript
export interface PlayerError {
    kind: string;
    message: string;
}

export interface DeveloperError {
    kind: string;
    effect: 'none' | 'applied' | 'partial' | 'unknown';
    recovery: 'retryable' | 'correctable' | 'terminal' | 'escalate';
    detail: string;
    context: Record<string, unknown>;
}

export interface ErrorResponse {
    error: PlayerError | DeveloperError;
}
```

**Step 2: Update ApiError to parse structured response**

Replace the `ApiError` class:

```typescript
class ApiError extends Error {
    public playerError: PlayerError | null;

    constructor(
        public status: number,
        public body: unknown
    ) {
        const parsed = body as ErrorResponse | null;
        const message = parsed?.error && 'message' in parsed.error
            ? parsed.error.message
            : `API error ${status}`;
        super(message);
        this.name = 'ApiError';
        this.playerError = parsed?.error && 'message' in parsed.error
            ? parsed.error as PlayerError
            : null;
    }
}
```

**Step 3: Verify frontend builds**

Run: `cd apps/web && npm run check`
Expected: no type errors

**Step 4: Commit**

```bash
git add apps/web/src/lib/api.ts
git commit -m "feat: update frontend ApiError to parse structured error responses"
```

---

### Task 8: Integration Test and Final Verification

**Files:**
- Test: `apps/api/tests/test_api.py` (update existing API tests if they assert on old error format)

**Step 1: Run full test suite**

Run: `cd apps/api && python -m pytest tests/ -v --ignore=tests/test_persistence.py`
Expected: all pass

**Step 2: Check for any remaining ValueError catches**

Search for `except ValueError` in the session-related files to make sure none remain:

Run: `grep -rn "except ValueError" apps/api/app/api/routers/sessions.py apps/api/app/services/session_service.py`
Expected: no matches

**Step 3: Check for any remaining `raise ValueError` in domain layer**

Run: `grep -rn "raise ValueError" apps/api/app/domain/`
Expected: only `engine.py` line 33 (`Unknown command` — intentionally kept as ValueError since it's a programming error, not a domain error)

**Step 4: Run frontend check**

Run: `cd apps/web && npm run check`
Expected: no errors

**Step 5: Final commit and push**

```bash
# Add only the specific files that were updated
git add apps/api/tests/test_api.py
git commit -m "test: update existing tests for structured error model"
git push
```
