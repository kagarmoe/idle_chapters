# Error Design

## Why errors are designed this way

The design of Idle Chapters demonstrates my user-centric and standards-driven approach to error messages. I use three profile projections, which draw from  RFC 9457 (Problem Details for HTTP APIs) with extension members for state semantics (effect), recovery guidance, and ANSI Z535 signal word severity classification.

Projections transform a GameError for different audiences:

- player: minimal RFC 9457 (type, title, status) [TBD]
- developer: full RFC 9457 + Z535 extensions [Implemented]
- agent (future): RFC 9457 + extensions, no prose detail [TBD]

In Idle Chapters, errors are first-class design objects because they sit at the intersection of three concerns that pull in different directions:

1. **The tone contract.** A player should never feel blamed, pressured, or confused. "Invalid input" violates the emotional safety the game promises. Errors the player sees must sound like the world gently redirecting them, not a system rejecting them.

2. **Developer needs.** A developer debugging a 409 needs to know exactly what happened to state, whether retry is safe, and what the player should do differently. Vague messages waste time; wrong messages cause incidents.

3. **Machine consumers.** An AI agent or frontend client needs to branch on structured fields, not parse prose. It needs `effect`, `recovery`, and `context` — not a sentence.

One error event, three audiences, three different truths. The design solves this with **projections**: a single internal error model that renders differently depending on who is looking.

## How it works

### The error is not a message

The core insight is that an error is a **state transition with consequences**, not a string. When something goes wrong, the system records:

- **What kind of thing went wrong** (`kind`) — a stable, machine-usable classification
- **What happened to state** (`effect`) — did anything change? is the system consistent?
- **Whether and how to recover** (`recovery`) — retry? fix input? give up? call a human?
- **Domain context** (`context`) — the IDs, counts, and data relevant to this specific failure

Messages are then *projected* from this internal model for each audience, not written directly.

### Three layers

```
Domain (pure exceptions)
    ↓ service layer catches and translates
GameError (structured model: kind + effect + recovery + context)
    ↓ projection at the boundary
Player / Developer / CLI / Agent (audience-specific rendering)
```

**Layer 1: Domain exceptions** (`domain/errors.py`). The game domain raises typed exceptions like `SessionNotFound` or `ActionNotEligible`. These carry only domain data — a session ID, an action ID, a list of unmet conditions. They know nothing about HTTP, projections, or error formatting.

**Layer 2: GameError** (`services/errors.py`). The service layer catches domain exceptions and constructs a `GameError` — the single structured model for all errors. GameError adds the fields that the domain shouldn't know about: effect on state, recovery guidance, HTTP status, and severity classification.

**Layer 3: Projections**. At the system boundary (API, CLI, or future agent interface), the GameError is projected for its audience.

### Projections

Each projection answers a different question:

**Player projection** — "What does the world say?"

Minimal. Tone-contract-compliant. Uses templates from `assets/error_templates.json` so the player reads something like *"That doesn't seem possible right now. Maybe explore a bit more first."* instead of a status code. Returns only `type`, `title`, and `status` per RFC 9457. No technical detail, no state semantics, no blame.

**Developer projection** — "What happened, exactly?"

Full RFC 9457 response with extension members. Includes a three-panel detail message adapted from ANSI Z535 safety labels:

- **WHAT** — the specific failure
- **MEANS** — the impact on system state
- **DO** — the recovery action

Plus a signal word (DANGER, WARNING, CAUTION, NOTICE) derived from effect and recovery, so severity is visible at a glance.

**CLI projection** — "What does the player see in the terminal?"

Reuses the player templates, formatted for terminal output. In verbose mode (`-v` / `--verbose`), prepends the Z535 signal word and renders the three-panel detail to stderr. This is the projection Phase C (beads issue `chapters-vxv`) implemented, in `idle_chapters/ui/errors.py`.

**Agent projection** (future) — "What do I branch on?"

Structured fields without prose. An agent doesn't read detail text — it branches on `type`, `effect`, and `recovery` to decide its next action.

### Severity classification (Z535 signal words)

Rather than inventing a severity scale, the design adopts ANSI Z535, the standard used on safety labels. The signal word is derived from two axes:

| | State is fine (`none`) | State mutated (`applied`) | State diverged (`partial`) | State unknown (`unknown`) |
|---|---|---|---|---|
| **Can retry** | CAUTION | CAUTION | WARNING | DANGER |
| **Can fix input** | CAUTION | CAUTION | WARNING | DANGER |
| **Path closed** | NOTICE | NOTICE | WARNING | DANGER |
| **Needs a human** | CAUTION | WARNING | DANGER | DANGER |

The rule: **effect determines the floor, recovery can raise it.** If the system doesn't know what happened to state, it's always DANGER regardless of recovery. If state is fine and the path is simply closed, it's NOTICE — important information, but nothing is broken.

### Player-facing templates

Templates live in `assets/error_templates.json`, validated by `schemas/error_templates.schema.json`. Each error kind has a `template` (with `{field}` placeholders filled from context) and a `fallback` for graceful degradation.

Every template must pass the tone contract validation checklist:
1. Is the player emotionally safe?
2. Is nothing required of them?
3. Does the message feel complete as-is?

Templates never use language expressing fear, pressure, urgency, scarcity, deficit, blame, or failure. The player is gently redirected, never rejected.

## Implementation status

| Layer | Status | Location |
|---|---|---|
| Domain exceptions | Done | `idle_chapters/domain/errors.py` |
| GameError model | Done | `idle_chapters/services/errors.py` |
| Player templates | Done | `assets/error_templates.json` |
| API exception handler | Done | `idle_chapters/api/server.py` |
| API projections (player + developer) | Done | `GameError.project_player()`, `GameError.project_developer()` |
| CLI projection (Phase C) | Done | `idle_chapters/ui/errors.py` (`print_error`), `--verbose` flag in `main.py` |
| Agent projection | Future | Design only |

### What Phase C changed

The CLI game now routes its error paths through the structured error model. `idle_chapters/ui/errors.py` renders player-facing copy (`print_error`, `invalid_choice`), with `main.py` exposing a `-v` / `--verbose` flag (`set_verbose`) that prepends the Z535 signal word and sends the three-panel WHAT/MEANS/DO detail to stderr. Concretely:

- Both welcome menu misses and cottage choices render `intent_no_match` via `print_error(invalid_choice(...))`.
- Save failures (`IOError`) render `persistence_failure`.
- Auto-recovering load notices stayed inline, reworded to be tone-contract-compliant (a corrupt/missing save is not an error the player must act on).
- Schema-validation detail is verbose-only stderr, so the normal player never sees it.

ANSI colors for signal words were deliberately skipped; add if terminal output grows richer.

## Standards

- **RFC 9457** (Problem Details for HTTP APIs) — the response format for API errors
- **RFC 9110** (HTTP Semantics) — status code definitions
- **ANSI Z535** (Safety Signs and Colors) — signal word hierarchy and three-panel message structure
- **Tone contract** (`design-docs/game_design/tone_contract.md`) — emotional and linguistic constraints for all player-facing content
