# Storylet and engine contract

## Purpose

Define the shared contract between authored scenes/actions and the engine that executes them.
This document makes the action model explicit, clarifies where reusability lives, and defines how
location-dependent choices remain data-driven.

## Scene and action contract (minimal)

### Non-mutation rule

Scenes and actions are inert data. They never execute logic or mutate state.
They only declare eligibility, effects, and flow.

### 1) Eligibility (`when`)

Scenes and actions declare **what is allowed** using declarative conditions:

- Location (place or zone)
- Flags (set/not set)
- Visit counts (minimum visit count)
- Time (time of day or day index)
- Inventory counts or presence

Eligibility is **declarative** and **idempotent**. It never performs effects.

### 2) Outcomes (`effects`)

Actions may apply **state changes only**:

- Add/remove inventory counts
- Set/clear flags
- Move location
- Update visit counters

Effects are declarative. The engine is the only component that applies them.

### 3) Presentation (`prompt`, `result`, `result_variants`)

Actions provide text payloads:

- `prompt`: scene framing
- `result`: single stable outcome
- `result_variants`: repeatable variation without escalation

### 4) Repeatability

- Repeatable actions are modeled with `result_variants` and eligibility gating (e.g., once-per-day).
- Repeatability must not introduce pressure or escalation.

## Engine responsibilities (derived)

### 1) Eligibility evaluation

- Resolve `when` rules strictly from state.
- Never make up new rules not represented in data.
- Examples:
  - `pick_up_journal` is only eligible when `location=cottage_home` and `flags_not_set(journal_available)`.
  - `make_tea` is eligible when `location.capability.can_make_tea=true` (or `zone_not=town`).

### 2) Selection

- Choose among eligible content deterministically (seeded).
- Prefer unseen or long-cooldown variants where available.

### 3) Effect application

- Apply effects in a single, auditable step.
- Preserve idempotency for “catch-all” actions (e.g., `head_to_town` adds missing items).
- Reject effects that do not conform to schema.

### 4) View model output

- Emit renderable output:
  - `prompt`
  - `eligible_actions`
  - `visible_items` (takeable now)
  - `visible_npcs` (always-present + eligible)

### 5) NPC selection policy (social level)

- Use `places.profile.social_level` to decide how many NPCs surface and how often.
- Keep **always-present** NPCs in `places.visible_npcs`.
- Select additional NPCs from eligible candidates (spawn rules + flags + time + history).
- Prefer variety: avoid recent repeats using `seen_interactions` and cooldowns.
- Keep selection deterministic and seeded by state (location + day).

## Reusable actions vs scene graph

### Global actions (reusable)

- Actions live in a global catalog, not per-location copies.
- Examples: `make_tea`, `head_to_town`, `rest`, `look_around`.
- Actions define:
  - `intent_signature` (keywords/phrases)
  - default `result_variants`
  - `effects`
  - eligibility tied to location capabilities or flags

### Scene graph (local)

- A scene graph composes actions into a specific flow.
- `cottage_wake` is scene-specific and references global actions as choices.
- The graph is a local constraint; choices live in scenes.

### Location-dependent choices

- Keep actions reusable by gating eligibility rather than duplicating actions.
- Example:
  - `pick_up_journal` is global but only eligible in `cottage_home` and only once.
  - `head_to_town` is global and eligible from any non-town location.

## Content storage decisions

- Scenes are per-file and listed in a manifest.
- Actions are centralized in `assets/actions.json`.
- Conditions use a shared schema (`conditions.schema.json`).
- Player inventory uses `inventory_counts` as canonical; lists are derived for display.

## Example: first cottage wake flow (conceptual)

- `cottage_wake` → choices: `rest_longer`, `look_around`
- `rest_longer` → choice: `look_around`
- `look_around` → choices: `make_tea`, `pick_up_journal`, `head_to_town`
- `make_tea` → adds `chamomile_flower`, `black_tea`, `biscuits`
- `pick_up_journal` → adds `journal`, sets `journal_available`
- `head_to_town` → adds any missing items (catch-all)

This is a graph of choices composed from reusable actions and eligibility gates.

## Procedural item scattering (allowed pattern)

- Generators may create **content-shaped availability** (action-like records) that declare item presence.
- The engine never mutates state ad hoc; it only applies **declared effects** from validated content.
- Randomness must be **seeded from state** so item scattering is deterministic and testable.
- The engine’s role is limited to selecting eligible content and applying its effects.

## Notes

- The engine must not invent rules the scene/action schema can’t represent.
- If the engine needs a behavior not representable here, update the contract first.
