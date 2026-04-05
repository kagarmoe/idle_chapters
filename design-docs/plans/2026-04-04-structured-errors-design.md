# Structured Error Model Design

## Status

**Approved design** — ready for implementation planning.

## Standards

This design profiles two standards:

- **RFC 9457** (Problem Details for HTTP APIs) — defines a machine-readable error response format for HTTP APIs. This design implements a full RFC 9457 profile with extension members for state semantics and recovery guidance.
- **ANSI Z535** (Safety Signs and Colors) — defines a hazard communication hierarchy (DANGER, WARNING, CAUTION, NOTICE) and a three-panel message structure (hazard, consequence, avoidance). This design adopts the signal word hierarchy for error severity classification and the three-panel structure for developer-facing detail.

These standards were chosen because they solve complementary problems: RFC 9457 answers "how do I describe an API error to machines?" while Z535 answers "how do I communicate a hazard to humans so they understand the severity, consequence, and required action?"

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

The domain raises typed exceptions that carry only domain-relevant data. The domain has no knowledge of RFC 9457, Z535, or the structured error model.

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

The service layer catches typed domain exceptions and constructs a `GameError` — the single structured model for all errors in the system. GameError is an internal representation that serializes to RFC 9457 at the API boundary.

#### RFC 9457 Profile

GameError maps to RFC 9457 Problem Details as follows:

Note: RFC 9457 does not mandate any members as strictly required in the schema sense — `type` defaults to `"about:blank"` when absent, and all other members are advisory. The requirements below are **project-level constraints** that are stricter than the RFC. The player projection uses a reduced profile that omits `detail` and extension members.

| RFC 9457 Member | GameError Field | Project Requirement | Description |
|---|---|---|---|
| `type` | `kind` | All projections | URI: `urn:idle-chapters:error:{kind}`. Stable, machine-usable classification per RFC 9457 Section 3.1.1. |
| `title` | derived from `kind` | All projections | Human-readable summary, one per type, per RFC 9457 Section 3.1.2. For the player projection, `title` carries the rendered template message. |
| `status` | `http_status` | All projections | HTTP status code per RFC 9110. |
| `detail` | `detail` | Developer, agent | Z535 three-panel message (see below). Per RFC 9457 Section 3.1.4. Omitted from the player projection. |
| `instance` | generated | Developer | UUID-based URI identifying this specific occurrence, per RFC 9457 Section 3.1.5. Format: `urn:idle-chapters:occurrence:{uuid4}`. |
| `effect` | `effect` | Developer, agent | What happened to system state. Extension member per Section 4. |
| `recovery` | `recovery` | Developer, agent | Whether and how the failure can be resolved. Extension member. |
| `context` | `context` | Developer, agent | Structured domain data (IDs, counts, timestamps). Extension member. |
| `signal` | `signal` | Developer, agent, CLI | Z535 signal word indicating severity. Extension member. |

#### Extension Member: `effect`

Answers the question RFC 9457 does not address: **what happened to system state?**

| Value | Meaning |
|-------|---------|
| `none` | No state mutation occurred |
| `applied` | State was fully mutated and persisted |
| `partial` | State was computed but not fully persisted (divergence) |
| `unknown` | Cannot determine what happened to state |

#### Extension Member: `recovery`

Encodes whether and how a failure can be resolved — information that neither RFC 9457 nor HTTP status codes provide.

| Value | Meaning |
|-------|---------|
| `retryable` | Same request may succeed on retry |
| `correctable` | User/caller can fix the input and retry |
| `terminal` | This path is closed; a different action is needed |
| `escalate` | Requires operator or developer intervention |

#### Extension Member: `signal` (ANSI Z535)

Maps error severity to the Z535 signal word hierarchy. Signal words are ordered by severity and carry specific meaning per ANSI Z535.4:

| Signal Word | Z535 Definition | Software Adaptation | GameError Mapping |
|---|---|---|---|
| **DANGER** | Will cause death or serious injury | State is indeterminate; system may be inconsistent | `effect=unknown` or `effect=partial` + `recovery=escalate` |
| **WARNING** | Could cause death or serious injury | State has diverged; data integrity at risk but recoverable | `effect=partial` + `recovery=retryable` or `correctable` |
| **CAUTION** | Could cause minor injury | No state damage; user action needed | `effect=none` + `recovery=correctable` or `retryable` |
| **NOTICE** | Important information, no injury risk | Operation cannot proceed, but system is healthy | `effect=none` + `recovery=terminal` |

The signal is derived from the `effect` and `recovery` combination. The table below is exhaustive — every valid combination maps to exactly one signal word. The `applied` effect describes a successful mutation that produced an error in a subsequent step (e.g., state persisted but journal write failed); it is included for completeness and future use.

| Effect | Recovery | Signal | Rationale |
|---|---|---|---|
| `unknown` | `escalate` | DANGER | State indeterminate, requires investigation |
| `unknown` | `retryable` | DANGER | State indeterminate even if retry might help |
| `unknown` | `correctable` | DANGER | State indeterminate regardless of input correction |
| `unknown` | `terminal` | DANGER | State indeterminate, path closed |
| `partial` | `escalate` | DANGER | State diverged, manual intervention required |
| `partial` | `retryable` | WARNING | State diverged but retry may resolve |
| `partial` | `correctable` | WARNING | State diverged, different input may resolve |
| `partial` | `terminal` | WARNING | State diverged, path closed — needs attention |
| `applied` | `escalate` | WARNING | Mutation succeeded but downstream step failed |
| `applied` | `retryable` | CAUTION | Mutation succeeded, downstream retry may help |
| `applied` | `correctable` | CAUTION | Mutation succeeded, downstream input correction needed |
| `applied` | `terminal` | NOTICE | Mutation succeeded, no further action possible |
| `none` | `escalate` | CAUTION | No state damage but developer intervention needed |
| `none` | `retryable` | CAUTION | No state damage, retry may succeed |
| `none` | `correctable` | CAUTION | No state damage, user can fix input |
| `none` | `terminal` | NOTICE | No state damage, path closed, system healthy |

**Derivation rule:** `effect` determines the floor, `recovery` can raise it.
- `unknown` → always DANGER (state is indeterminate)
- `partial` + `escalate` → DANGER (diverged state requiring manual intervention)
- `partial` + other → WARNING (diverged but recoverable)
- `applied` + `escalate` or `retryable` → WARNING/CAUTION (mutation succeeded, downstream issue)
- `none` → CAUTION or NOTICE depending on whether action is possible

#### Z535 Three-Panel Detail

The `detail` field follows the ANSI Z535.4 three-panel product safety label structure, adapted for software:

| Z535 Panel | Adapted Label | Purpose |
|---|---|---|
| **Hazard** | `WHAT` | What happened — the specific failure |
| **Consequence** | `MEANS` | What it means for the system — the state impact |
| **Avoidance** | `DO` | What to do next — the recovery action |

Example:
```
WHAT: Write failed after engine applied effects to session abc-123.
MEANS: Player state was computed but not persisted. In-memory and database have diverged.
DO: Retry the request. If it persists, check database connectivity.
```

This structure ensures that every developer-facing error message answers three questions in a fixed, scannable order. The signal word (WARNING, in this case) indicates severity at a glance.

### Exception-to-GameError Mapping

| Domain Exception | Kind | Status | RFC 9110 Meaning | Effect | Recovery | Signal |
|---|---|---|---|---|---|---|
| `SessionNotFound` | `session_not_found` | 404 | Not Found — resource does not exist | `none` | `terminal` | NOTICE |
| `ActionNotEligible` | `action_not_eligible` | 409 | Conflict — request conflicts with current resource state | `none` | `correctable` | CAUTION |
| `IntentNoMatch` | `intent_no_match` | 422 | Unprocessable Entity — request understood but semantically invalid | `none` | `correctable` | CAUTION |
| `InsufficientInventory` | `insufficient_inventory` | 409 | Conflict — request conflicts with current resource state | `none` | `correctable` | CAUTION |
| `InvalidLocation` | `invalid_location` | 422 | Unprocessable Entity — request understood but semantically invalid | `none` | `correctable` | CAUTION |
| `SceneNotAvailable` | `scene_not_available` | 503 | Service Unavailable — server cannot handle the request right now | `none` | `retryable` | CAUTION |
| Unexpected (engine) | `engine_failure` | 500 | Internal Server Error — unexpected server-side failure | `unknown` | `escalate` | DANGER |
| Unexpected (persist) | `persistence_failure` | 503 | Service Unavailable — server cannot handle the request right now | `partial` | `retryable` | WARNING |
| Journal page missing | `journal_page_not_found` | 404 | Not Found — resource does not exist | `none` | `correctable` | CAUTION |

The service layer separates engine execution from persistence so it can distinguish `engine_failure` (effect unknown, DANGER) from `persistence_failure` (effect partial, WARNING):

```python
try:
    result = engine.step(state, action, action_id, repo)
except Exception as e:
    raise GameError(kind="engine_failure", effect="unknown", ...)  # DANGER

try:
    self._state_store.upsert_state(state)
    self._journal_store.append_page(result.journal_page)
except Exception as e:
    raise GameError(kind="persistence_failure", effect="partial", ...)  # WARNING
```

### Layer 3: Projections

The API and CLI layers project `GameError` for different audiences. Projection is determined by interaction context, not identity (RFC 9457 Section 3.1 notes that `detail` should be specific to the occurrence; projections extend this principle to the entire response shape).

**Projection selection (API):** `Accept-Projection` header. Default: `player`.

#### Player Projection

Template-based, tone-contract-compliant messages stored in `assets/error_templates.json` and validated by `schemas/error_templates.schema.json`.

Templates use `{field}` placeholders filled from `GameError.context`. Every kind has a fallback for graceful degradation. The player projection intentionally softens `escalate` recovery — players should never be told to "report this to a developer."

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

**RFC 9457 response shape (player):**

The player projection returns a minimal RFC 9457 body. The `title` serves as the rendered template message. Extension members are omitted — players do not need state or recovery semantics.

```json
{
    "type": "urn:idle-chapters:error:action_not_eligible",
    "title": "That doesn't seem possible right now. Maybe explore a bit more first.",
    "status": 409
}
```

#### Developer Projection

Full RFC 9457 body with all extension members and Z535 three-panel detail:

```json
{
    "type": "urn:idle-chapters:error:action_not_eligible",
    "title": "Action Not Eligible",
    "status": 409,
    "detail": "WHAT: Action gather_herbs failed conditions for session abc-123.\nMEANS: State unchanged. Action requires unmet conditions.\nDO: Check eligible actions via GET /v1/sessions/abc-123.",
    "instance": "urn:idle-chapters:occurrence:a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "effect": "none",
    "recovery": "correctable",
    "signal": "CAUTION",
    "context": {
        "action_id": "gather_herbs",
        "session_id": "abc-123",
        "unmet": ["flags_set: visited_garden"]
    }
}
```

#### Agent Projection (Future)

RFC 9457 body with extension members but without prose `detail` — agents don't read prose, they branch on `type`, `effect`, and `recovery`:

```json
{
    "type": "urn:idle-chapters:error:action_not_eligible",
    "title": "Action Not Eligible",
    "status": 409,
    "effect": "none",
    "recovery": "correctable",
    "signal": "CAUTION",
    "context": {
        "action_id": "gather_herbs",
        "session_id": "abc-123",
        "unmet": ["flags_set: visited_garden"]
    }
}
```

#### CLI Projection

Reuses player templates, formatted for terminal output via `ui/text.py`. The Z535 signal word is prepended in verbose mode:

```
CAUTION: That doesn't seem possible right now. Maybe explore a bit more first.
```

Full Z535 three-panel detail available via `--verbose` flag to stderr. CLI colors for signal words are left to implementation.

## Acceptance Criteria

- All player-facing templates pass tone contract review (`design-docs/game_design/tone_contract.md`)
- No template uses language expressing: fear, pressure, urgency, scarcity, deficit, blame, or failure
- Fallback messages also comply with tone contract
- API error responses conform to RFC 9457 (`type`, `title`, `status` in all projections; `detail` in developer and agent projections)
- Error `type` URIs follow the pattern `urn:idle-chapters:error:{kind}`
- HTTP status codes align with RFC 9110 semantics
- Developer projection includes Z535 three-panel structure (WHAT / MEANS / DO) and signal word
- Signal word is derived from `effect` and `recovery` per the mapping table
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
schemas/error_response.schema.json         -- RFC 9457 API error response contract
tests/test_domain_errors.py                -- Domain exceptions carry correct data
tests/test_game_error_mapping.py           -- Service maps exceptions to GameError correctly
tests/test_error_projections.py            -- Each projection renders RFC 9457 responses
tests/test_error_templates.py              -- Templates validate, placeholders resolve, tone compliance
```

### Modified Files

```
apps/api/app/domain/effects.py             -- ValueError -> InsufficientInventoryError
apps/api/app/domain/engine.py              -- ValueError -> typed exceptions
apps/api/app/domain/selector.py            -- ValueError -> SceneNotAvailable
apps/api/app/domain/scene_generator.py     -- ValueError -> InvalidLocation
apps/api/app/services/session_service.py   -- Catch typed exceptions, construct GameError
apps/api/app/api/app.py                    -- GameError exception handler
apps/api/app/api/routers/sessions.py       -- Remove try/except, let GameError propagate
apps/api/app/api/models.py                 -- Pydantic response models for RFC 9457
apps/web/src/lib/api.ts                    -- Parse RFC 9457 error response
```

### Error Response Schema (`schemas/error_response.schema.json`)

RFC 9457 response contract. Uses `oneOf` to distinguish player and developer projection shapes:

```json
{
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Error Response (RFC 9457 Profile)",
    "description": "Problem Details response per RFC 9457 with Z535 and state-semantics extensions.",
    "type": "object",
    "required": ["type", "title", "status"],
    "properties": {
        "type": {
            "type": "string",
            "format": "uri",
            "pattern": "^urn:idle-chapters:error:.+$"
        },
        "title": { "type": "string" },
        "status": { "type": "integer", "minimum": 400, "maximum": 599 },
        "detail": { "type": "string" },
        "instance": { "type": "string", "format": "uri" },
        "effect": {
            "type": "string",
            "enum": ["none", "applied", "partial", "unknown"]
        },
        "recovery": {
            "type": "string",
            "enum": ["retryable", "correctable", "terminal", "escalate"]
        },
        "signal": {
            "type": "string",
            "enum": ["DANGER", "WARNING", "CAUTION", "NOTICE"]
        },
        "context": { "type": "object" }
    },
    "oneOf": [
        {
            "description": "Player projection — minimal RFC 9457",
            "required": ["type", "title", "status"],
            "not": { "required": ["effect"] }
        },
        {
            "description": "Developer/agent projection — full RFC 9457 with extensions",
            "required": ["type", "title", "status", "effect", "recovery", "signal"]
        }
    ]
}
```

## Phased Rollout

- **Phase A:** Session endpoints (`/sessions/{id}/action`, `/sessions/{id}/intent`) — richest error cases, proves the model
- **Phase B:** All API endpoints (world, players, journal)
- **Phase C:** CLI interface with Z535 signal word display

## References

- [RFC 9457: Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457) — error response format
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) — status code definitions
- [ANSI Z535.4: Product Safety Signs and Labels](https://www.nema.org/standards/z535) — signal word hierarchy and three-panel message structure
