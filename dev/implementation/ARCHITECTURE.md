# ARCHITECTURE.md

## Purpose

Idle Chapters is a cozy, text-first world that advances in small “chapters.”
The project is a technical writing portfolio artifact that demonstrates:

- schema-driven content systems (validation + contracts)
- an engine/content separation (domain logic vs authored content)
- an API-first architecture (FastAPI) with persistence (MongoDB)
- an interchangeable interface layer (API now, CLI later)
- a journal artifact that functions as UI, narrative record, and inventory ledger
- - procedural generation of storylets/interactions constrained by schemas + lexicons

The first playable version presents the player with “Option 1 / Option 2 / Option 3” choices.
A later version supports a CLI for navigation and interaction.

## Non-goals (for v1)

- no graphical UI
- no full procedural *world* generation at load time (zones/places/NPCs/items are authored assets in v1)
- no “winning,” combat, or optimization pressure
- no complex economy
- no complicated time simulation beyond simple ticks

## Core Design Contract (high-level)

- The player is a presence; self-definition is optional.
- The tone is gentle; language is constrained by lexicons.
- The world is experienced through structured journal pages.
- Inventory is real, but the journal is the primary interface to it.

## Primary Output Artifact: JournalPage

A gameplay step produces a JournalPage.

Instead of “engine returns a paragraph,” the system returns a structured page (YAML frontmatter + Markdown body) that captures:

- where you are (place_id / zone context)
- what happened (storylet / interaction / recipe framing)
- what was used or gained (inventory deltas and/or ingredient picks)
- tone anchors (mood, need, tags, sensory prompts)
- a stable record that can be stored and rendered anywhere

### Engine Contract

Engine.step(state, command) -> StepResult

StepResult:

- journal_page: JournalPage (validated structure)
- choices: [Choice, …] (v1 menu)
- state: updated PlayerState (persistable)
- debug: selection metadata (portfolio visibility)

The API and CLI both render the returned journal_page.

## System Layers

### Content Layer (authored, validated, read-only at runtime)

Stored as YAML instance files and validated with JSON Schemas (YAML format).

- assets/
  - places.yaml
  - npcs.yaml
  - collectibles.yaml
  - interactions.yaml
  - tea.yaml
  - spells.yaml
  - storylets.yaml (next major content file)
  - journal_templates.yaml
- lexicons/
  - descriptive_lexicon.yaml
  - not_allowed_lexicon.yaml

Schemas live under schemas/ and are used to validate asset/lexicon instances at load time.

### Domain Layer (engine)

Pure Python modules that:

- evaluate conditions
- select eligible content
- apply effects to state
- assemble a JournalPage (frontmatter + Markdown body)

The domain layer must not know about FastAPI or Mongo.

#### Generation (v1)

In v1, storylets and many interaction lines are produced *procedurally at runtime* (per step),
not pre-authored as a fixed catalog.

The generator is a domain component that:

- takes the current state (place_id, time/tick, inventory, flags) and a seed
- consults authored assets (places, NPCs, collectibles, recipes, lexicons, journal templates)
- emits a Storylet-like object and/or interaction candidates that conform to the relevant schemas
- is constrained by lexicons (including Not_Allowed) and the tone contract
- returns debug metadata (seed, template ids, constraint hits) for portfolio-grade inspectability

This is distinct from “full procedural world generation at load time.” The *world* (zones/places/NPCs/items) is authored;
the *moment-to-moment* storylet/interaction content is generated.

### Persistence Layer (MongoDB)

MongoDB stores:

- player/session state snapshots (latest)
- journal pages (append-only)
- optional event log (append-only) for debugging/audit

MongoDB does not “generate tables.” Schemas validate assets and define API DTOs; Mongo stores runtime state and history.

### Interface Layer(s)

- FastAPI: primary portfolio interface, with OpenAPI docs
- CLI (later): uses the API as a client (best separation), or runs the engine locally (fallback)

## Data Model Strategy

### Schemas (what they do)

Schemas are used for:

1. validating YAML assets/lexicons/journal templates at load time
2. defining request/response DTOs for the API (Pydantic)
3. documenting system invariants (through comments + constraints)

Schemas are not used to create relational tables.
Mongo collections are shaped by Pydantic models and enforced by application logic and tests.

### Assets (what they do)

Assets provide authored world content.
They are loaded into an in-memory ContentRepo with indices that allow fast lookup:

- storylets by place_id / zone_id / tags
- interactions by npc_kind / npc_id / place_id
- collectibles by item_id / tags / usable_in
- journal templates by entry_type / tags

### State (what it does)

State is the minimal runtime truth required to:

- pick eligible content
- apply effects
- track inventory and flags
- persist progress

Example state elements:

- session_id
- current_place_id
- inventory counts
- flags / unlocked markers
- relationship affinity counters (optional, later)
- time ticks (optional)

## Storylets: Unit of Experience

A storylet is the core unit the engine selects to describe “what happens next.”

A storylet:

- is anchored to a place (or zone)
- has conditions that must be true to occur
- contains choice options (v1) or sets up an interaction
- applies effects (inventory, flags, time)
- provides guidance for journal rendering (entry_type, mood/need/tags)

Storylets connect authored world content to the journal artifact.

In v1, storylets may be either authored (assets/storylets.yaml) **or generated on demand** using the same schema shape.
The engine treats both the same: it evaluates conditions, applies effects, and renders a JournalPage.

## Selection Model (v1)

Selection is simple and explainable (portfolio-friendly):

- filter eligible storylets based on current place and conditions
- optionally weight by tags/time/rarity
- choose deterministically with a seed (if provided) for testability
- optionally generate a fresh storylet/interaction candidate for the current context (seeded), then select among candidates
- record debug metadata (eligible_count, selected_storylet_id)

## Effects Model (v1)

Effects are reducer-like operations applied to state. Keep small and composable:

- inventory.add(item_id, qty)
- inventory.remove(item_id, qty)
- flags.set(flag_id)
- flags.clear(flag_id)
- location.set(place_id)
- time.advance(ticks) (optional)

Effects are validated by schema and by runtime checks (e.g., cannot remove below zero unless explicitly allowed).

## Journal Rendering (v1)

Journal rendering uses:

- journal_templates.yaml to select a template by entry_type and tags
- lexicons to constrain generated phrases (and avoid disallowed words)
- place + storylet context to fill prompts and sensory details
- ingredient selection rules (place_policy order: same_place > same_zone > any_place)

The renderer must remain safe without player identity fields.

## API Surface (v1)

Required endpoints:

- POST /sessions
  - create session, initialize state snapshot
- GET /sessions/{session_id}
  - return summary of current state + last journal page pointer
- POST /sessions/{session_id}/step
  - input: choice/action
  - output: StepResult (journal_page + choices + debug)
- GET /world/places, /world/npcs, /world/items, /world/recipes
  - read-only assets (portfolio visibility)
- GET /sessions/{session_id}/journal
  - list journal pages
- GET /sessions/{session_id}/journal/{page_id}
  - return one page

Optional (for portfolio clarity):

- GET /sessions/{session_id}/events

## CLI (v2)

CLI is a client of the API:

- starts/loads a session
- prints the last journal page
- shows numeric choices
- submits a step
- repeats

This demonstrates:
- separation of concerns
- reusable domain logic behind multiple interfaces

## Testing Strategy

- unit tests:
  - schema validation of all assets
  - cross-file foreign key checks
  - condition evaluation and effect reducers
  - deterministic selection with seeds
- integration tests:
  - API session creation + step
  - Mongo persistence round trip
  - journal page storage and retrieval

## Observability (portfolio-friendly)

Every step should be inspectable:

- selected_storylet_id
- eligible_count
- applied_effects list
- inventory deltas
- final tags/mood/need used in rendering
