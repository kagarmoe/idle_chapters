# Structured Error Model Design

## Status

**Approved design** — ready for implementation planning.

## Problem

The current error flow is: `ValueError` (domain) -> `HTTPException` (router) -> `{"detail": "..."}` (JSON) -> `ApiError` (frontend). This creates:

- No stable, machine-usable classification of what went wrong
- No indication of what happened to system state
- No guidance on whether or how to recover
- A single string message that cannot serve players, developers, and agents simultaneously

Errors are treated as messages. They need to be treated as **state transitions with consequences and recovery paths**.

## Core Insight

An error is not a message. It is a state transition with consequences and possible recovery paths. Once that is true:

- Messages become projections of the error, not the error itself
- HTTP status codes become partial views
- Different consumers get different truths from the same event

## Design

### Layer 1: Typed Domain Exceptions

Location: `apps/api/app/domain/errors.py`

The domain raises typed exceptions that carry only domain-relevant data. The domain has no knowledge of the structured error model.

```python
class SessionNotFound(Exception):
    def __init__(self, session_id: str): ...

class ActionNotEligible(Exception):
    def __init__(self, action_id: str, session_id: str, unmet_conditions: list[str]): ...

class IntentNoMatch(Exception):
    def __init__(self, input_text: str, available_actions: list[str]): ...

class InsufficientInventory(Exception):
    def __init__(self, item_id: str, required: int, available: int): ...

class InvalidLocation(Exception):
    def __init__(self, location_id: str): ...

class SceneNotAvailable(Exception):
    def __init__(self, session_id: str): ...
```

### Layer 2: GameError (Service Layer)

Location: `apps/api/app/services/errors.py`

The service layer catches typed domain exceptions and constructs a `GameError` — the single structured model for all errors in the system.

**Fields:**

| Field | Type | Purpose |
|-------|------|---------|
| `kind` | `str` (enum) | Stable, machine-usable classification |
| `effect` | `str` (enum) | What happened to system state |
| `recovery` | `str` (enum) | Whether and how the failure can be resolved |
| `detail` | `str` | Z535-style: WHAT / MEANS / DO (developer-facing) |
| `context` | `dict` | Structured data for machine consumers (IDs, counts, timestamps) |

**Effect values:**

| Value | Meaning |
|-------|---------|
| `none` | No state mutation occurred |
| `applied` | State was fully mutated and persisted |
| `partial` | State was computed but not fully persisted (divergence) |
| `unknown` | Cannot determine what happened to state |

**Recovery values:**

| Value | Meaning |
|-------|---------|
| `retryable` | Same request may succeed on retry |
| `correctable` | User/caller can fix the input and retry |
| `terminal` | This path is closed; a different action is needed |
| `escalate` | Requires operator or developer intervention |

### Exception-to-GameError Mapping

| Domain Exception | Kind | HTTP Status | Conventional Meaning | Effect | Recovery |
|---|---|---|---|---|---|
| `SessionNotFound` | `session_not_found` | 404 | Not Found -- resource does not exist | `none` | `terminal` |
| `ActionNotEligible` | `action_not_eligible` | 409 | Conflict -- request conflicts with current resource state | `none` | `correctable` |
| `IntentNoMatch` | `intent_no_match` | 422 | Unprocessable Entity -- request understood but semantically invalid | `none` | `correctable` |
| `InsufficientInventory` | `insufficient_inventory` | 409 | Conflict -- request conflicts with current resource state | `none` | `correctable` |
| `InvalidLocation` | `invalid_location` | 422 | Unprocessable Entity -- request understood but semantically invalid | `none` | `correctable` |
| `SceneNotAvailable` | `scene_not_available` | 503 | Service Unavailable -- server cannot handle the request right now | `none` | `retryable` |
| Unexpected (engine) | `engine_failure` | 500 | Internal Server Error -- unexpected server-side failure | `unknown` | `escalate` |
| Unexpected (persist) | `persistence_failure` | 503 | Service Unavailable -- server cannot handle the request right now | `partial` | `retryable` |

The service layer separates engine execution from persistence so it can distinguish `engine_failure` (effect unknown) from `persistence_failure` (effect partial -- state computed but not saved):

```python
try:
    result = engine.step(state, action, action_id, repo)
except Exception as e:
    raise GameError(kind="engine_failure", effect="unknown", ...)

try:
    self._state_store.upsert_state(state)
    self._journal_store.append_page(result.journal_page)
except Exception as e:
    raise GameError(kind="persistence_failure", effect="partial", ...)
```

### Layer 3: Projections

The API and CLI layers project `GameError` for different audiences. Projection is determined by interaction context, not identity.

**Projection selection (API):** `Accept-Projection` header. Default: `player`.

#### Player Projection

Template-based, tone-contract-compliant messages stored in `assets/error_templates.json` and validated by `schemas/error_templates.schema.json`.

Templates use `{field}` placeholders filled from `GameError.context`. Every kind has a fallback for graceful degradation.

```json
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
    }
}
```

**Response shape:**
```json
{
    "error": {
        "kind": "action_not_eligible",
        "message": "That doesn't seem possible right now. Maybe explore a bit more first."
    }
}
```

#### Developer Projection

Z535-style detail following the hazard communication standard: WHAT happened, what it MEANS, what to DO.

```json
{
    "error": {
        "kind": "action_not_eligible",
        "effect": "none",
        "recovery": "correctable",
        "detail": "WHAT: Action gather_herbs failed conditions for session abc-123.\nMEANS: State unchanged. Action requires unmet conditions.\nDO: Check eligible actions via GET /v1/sessions/abc-123.",
        "context": {
            "action_id": "gather_herbs",
            "session_id": "abc-123",
            "unmet": ["flags_set: visited_garden"]
        }
    }
}
```

#### Agent Projection (Future)

Same as developer but without prose `detail` -- agents don't read prose:

```json
{
    "error": {
        "kind": "action_not_eligible",
        "effect": "none",
        "recovery": "correctable",
        "context": {
            "action_id": "gather_herbs",
            "session_id": "abc-123",
            "unmet": ["flags_set: visited_garden"]
        }
    }
}
```

#### CLI Projection

Reuses player templates, formatted for terminal output via `ui/text.py`. Developer detail available via `--verbose` flag to stderr.

## Acceptance Criteria

- All player-facing templates pass tone contract review (`design-docs/game_design/tone_contract.md`)
- No template uses language expressing: fear, pressure, urgency, scarcity, deficit, blame, or failure
- Fallback messages also comply with tone contract
- All error kinds map to a stable HTTP status code
- Developer projection follows Z535 structure (WHAT / MEANS / DO)
- `effect` field accurately reflects state mutation for every error path
- `recovery` field provides actionable, correct guidance
- Error templates are schema-validated JSON in `assets/`
- Domain exceptions carry structured data, not formatted strings

## File Layout

### New Files

```
apps/api/app/domain/errors.py              -- Typed domain exceptions
apps/api/app/services/errors.py            -- GameError model + projection logic
assets/error_templates.json                -- Player-facing templates
schemas/error_templates.schema.json        -- Validates the templates
schemas/error_response.schema.json         -- API error response contract
tests/test_domain_errors.py                -- Domain exceptions carry correct data
tests/test_game_error_mapping.py           -- Service maps exceptions to GameError correctly
tests/test_error_projections.py            -- Each projection renders as expected
tests/test_error_templates.py              -- Templates validate, placeholders resolve, tone compliance
```

### Modified Files

```
apps/api/app/domain/effects.py             -- ValueError -> InsufficientInventoryError
apps/api/app/domain/engine.py              -- ValueError -> typed exceptions
apps/api/app/domain/conditions.py          -- ValueError -> ActionNotEligible
apps/api/app/services/session_service.py   -- Catch typed exceptions, construct GameError
apps/api/app/api/routers/sessions.py       -- Catch GameError, project for audience
apps/api/app/api/models.py                 -- Pydantic response models for error projections
apps/web/src/lib/api.ts                    -- Parse structured error response
```

## Phased Rollout

- **Phase A:** Session endpoints (`/sessions/{id}/action`, `/sessions/{id}/intent`) -- richest error cases, proves the model
- **Phase B:** All API endpoints (world, players, journal)
- **Phase C:** CLI interface
