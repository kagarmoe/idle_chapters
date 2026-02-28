# V1_PLAYABLE_PLAN.md

## Goal of this plan

Produce a working v1 that is demoable via FastAPI:

- creates a session
- returns a journal page for “what happens next”
- offers eligible actions (intent-based)
- applies effects and persists state (inventory_counts canonical)
- stores journal pages as the primary record

This plan is intentionally granular: file names, milestones, and acceptance criteria.

## Milestone 0 — Repo organization (1 pass)

### Create/confirm directories

- assets/
- lexicons/
- schemas/
- journal/ (already exists)
- app/
  - api/
  - content/
  - domain/
  - persistence/
  - services/
- tests/
- dev/implementation/ (keep historical docs)

### Acceptance criteria

- repo layout matches architecture assumptions
- assets/schemas/lexicons are in stable locations

---

## Milestone 1 — Content loading + schema validation (hard requirement)

### 1.1 Add a loader

File: `app/content/loader.py`

- load JSON from a path
- validate against schema (jsonschema)
- return parsed dict/list

### 1.2 Add content registry config

File: `app/content/manifest.py`

- define which files exist and where:
  - schemas paths
  - assets paths
  - lexicon paths
- one place to update later

### 1.3 Build ContentRepo + indices

- `ContentProvider` (file-based in V1; loads JSON from the repo)
- Later (optional): `MongoContentProvider` (only if we need live editing / multi-pack serving)

File: `app/content/repo.py`

**V1 decision:** load all validated *asset content* into memory at process start, then serve lookups from indices.
MongoDB is reserved for *runtime data* (sessions, state, journal pages), not static world content.

Scene manifest loading (v1):
- read `assets/scenes/manifest.json`
- load each scene file listed there
- validate against `scene.schema.json`

Why this is the right default for V1:
- **Simplicity**: no migrations, no content database bootstrapping, no dual-source-of-truth.
- **Speed**: after startup, content access is pure in-process dict lookup.
- **Fail-fast validation**: schema + cross-file checks run once at boot and crash loudly if broken.
- **Git-native workflow**: edit JSON → run tests → commit. No admin UI required.
- **Determinism & testability**: generator behavior depends on versioned content, not mutable DB rows.

Tradeoffs and when Mongo-backed content becomes worth it:
- **Pros of putting content in Mongo**
  - Live editing via UI (non-dev authoring)
  - Hot reload without process restart
  - Serving multiple content packs or per-tenant worlds from a single service
  - Potentially less startup time for very large content sets (at the cost of runtime queries)
- **Cons (and why we avoid it in V1)**
  - Introduces migrations/versioning problems for content
  - Requires seeding and environment coordination (dev/stage/prod drift)
  - Adds runtime dependency and query paths for every generation step unless carefully cached
  - Makes debugging harder (“why did this happen?” can become “which version of content was in DB?”)

**Design for future flexibility (without paying the cost now):**
- Keep `ContentProvider` as the abstraction boundary.
- `ContentRepo` is an in-memory cache + index layer; it should not care where the raw docs came from.
- If we ever add `MongoContentProvider`, it should still produce the same validated in-memory structures
  (and ideally the same indices) to keep the engine unchanged.

#### Indices built by ContentRepo

Load all validated assets into memory and build indices:

- places_by_id
- zones_by_id (if needed)
- collectibles_by_id
- npcs_by_id
- interactions_by_id
- interactions_by_npc_kind
- interactions_by_place_id
- tea_by_id
- spells_by_id
- actions_by_id
- scenes_by_id (from per-file scenes + manifest)
- journal_templates_by_entry_type
- lexicon_by_key

Implementation notes (practical):
- Normalize IDs to strings and enforce uniqueness per file (fail fast).
- Consider storing `source_file`/`source_line` metadata for better validation errors (optional but very helpful).
- Indices should be plain dicts/DefaultDicts—keep them boring and transparent.

### 1.4 Cross-file integrity checks

File: `app/content/validators.py`

Validate at load time:

- every place_id reference exists
- every npc_id reference exists
- collectible origin_ref points to a real place (when origin_scope indicates place)
- interactions dependencies reference real npc/place/time tokens
- tea/spell ingredient_ref resolves to:
  - a collectible_id OR
  - an any: substitution token (allowed)
- lexicon scope:
  - Global OR place_id that exists

### Acceptance criteria

- Running a single command loads everything and prints “OK”
- Any missing place_id/npc_id/item_id fails fast with a clear message
- Unit tests exist for loader + validators

---

## Milestone 2 — Scenes + actions v1 (procedural-first interactions)

Scenes are authored graphs of reusable actions. In v1, **procedural generation is used for interactions** and ambient variation, while scenes/actions are authored and validated.

### 2.0 Decide the v1 Scene + Action contract (one-time decisions)

These decisions keep the code simple and testable:

- **Binding**: v1 scenes are place-bound (use `place_id`, not `zone_id`).
- **Choices**: scenes own the graph; actions are reusable.
- **Determinism**: every selection step accepts an optional `seed`.
- **Debugability**: selections include debug metadata (seed + template ids + constraint notes).

### 2.1 Confirm/adjust `scene.schema.json`, `actions.schema.json`, `conditions.schema.json`

Files: `schemas/scene.schema.json`, `schemas/actions.schema.json`, `schemas/conditions.schema.json`

Add (or confirm) support for:

- `when` structure usable by both authored and generated actions
- `effects` structure compatible with reducer functions

Acceptance check:

- a generated action/interaction can validate without requiring fully authored prose

### 2.2 Implement Scene/Action models (internal)

Files: `app/domain/scene.py`, `app/domain/action.py` (or unified models)

- Define lightweight Scene/Action types (Pydantic model or dataclass) that match the schema shapes.
- Scene fields:
  - `scene_id: str`
  - `place_id: str`
  - `entry_node: str`
  - `nodes: list[SceneNode]`
- SceneNode fields:
  - `node_id: str`
  - `action_ref: str`
  - `choices: list[str]`
- Action fields:
  - `action_id: str`
  - `label: str`
  - `when: dict | None`
  - `result: str | None`
  - `result_variants: list[str]`
  - `intent_signature: dict`
  - `effects: dict`

### 2.3 Implement procedural interaction generator (core v1 feature)

File: `app/domain/interaction_generator.py`

Responsibilities:

- Inputs:
  - `state` (place_id, inventory, flags, time_tick)
  - `repo` (places/npcs/items/recipes/interactions/templates/lexicons)
  - `seed` (optional)

- Output:
  - interaction candidates (or N candidates)

Implementation steps:

1) **Pick an entry_type**
   - Start rule: default to `tea` unless a place has a “threshold” tag for `spell`.
   - Later: weight by time_tick or recent history.

2) **Pick a template family** (not the journal template; an interaction “shape”)
   - Example families: `arrival`, `small_find`, `offer_help`, `quiet_notice`, `threshold_call`.

3) **Construct a prompt/title seed**
   - Use descriptive lexicon for sensory anchors; avoid not_allowed lexicon.
   - Keep the prompt short; journal templates can expand it.

4) **Construct 3 choices**
   - Each choice has:
     - `choice_id` ("1","2","3")
     - `label` (short text)
     - `effects` (small reducers)
   - Keep effects conservative in v1:
     - add/remove 0–2 items
     - set/clear at most 1 flag
     - optional move location (rare)

5) **Attach journal hints**
   - `need_hint`, `mood_hint`, `tags` consistent with entry_type.

6) **Attach debug metadata**
   - seed used
   - family/template id
   - key constraint decisions (e.g., “spell disallowed: not a threshold place”)

7) **Validate**
   - Validate the generated object against `interactions.schema.json`.
   - If invalid, fail fast with readable error (this is portfolio-grade).

### 2.4 Implement interaction candidate selection (generated + authored)

File: `app/domain/selector.py`

- Add a function `generate_candidates(state, repo, seed, n=3)`.
- Add a function `merge_with_authored(candidates, authored)`.
- Add selection:
  - deterministic selection by seed
  - prefer authored anchors if explicitly “pinned” (optional later)

### 2.5 Author a minimal anchor set (optional but recommended)

File: `assets/scenes/manifest.json`

Target: **6–10** scenes total.

Purpose:
- stable examples
- regression fixtures
- guarantee at least one scene exists per major zone

Guidelines:
- keep prose minimal
- keep effects conservative
- keep tags simple

### 2.6 Add scenes/actions to ContentRepo (authored anchors)

File: `app/content/repo.py`

- Load and index authored scenes from the manifest and actions from `assets/actions.json`.
- Index by `place_id`.

### 2.7 Tests for generation (required)

Files:
- `tests/test_scene_generation.py` (to be renamed when interaction generator replaces scenes)

Test cases:
- generator returns valid interaction candidates
- generator output validates against schema
- determinism: same seed + same state => same ids and labels
- safety: generator output contains no disallowed words (basic check via not_allowed lexicon)

### Acceptance criteria (Milestone 2)

- procedural generator can emit valid interactions for any supported place
- generated interactions validate against `interactions.schema.json`
- selector can merge generated candidates with authored anchors (if present)
- at least one end-to-end step can run using a generated interaction

---

## Milestone 3 — Journal templates + renderer (make journal first-class)

### 3.0 Define JournalPage as the step output

File: `app/domain/step_result.py`

- Define `StepResult` to include:
  - `journal_page` (frontmatter dict + markdown body)
  - `eligible_actions`
  - `debug` (seed, selected_action_id, eligible_count)

This keeps the API/CLI thin: they render the returned journal page.

### 3.1 Confirm journal template loading

File: `app/content/repo.py`

- load `journal_templates.json`
- index templates by entry_type (and optionally by tags)

### 3.2 Implement journal renderer

File: `app/domain/journal_renderer.py`

Inputs:

- place_id
- entry_type
- scene/action (selected)
- state snapshot (inventory/flags as needed)
- ingredient picks (optional, based on action/interaction tags)

Outputs:

- JournalPage object:
  - frontmatter fields aligned with journal_page.schema
  - markdown body assembled from template + scene/action context

### 3.3 Ingredient picking (locality rules)

File: `app/domain/ingredient_picker.py`

Implement:

- place_policy order: same_place (strict) > same_zone > any_place
- use places.json zone_id mapping (no heuristics once places are loaded)
- ensure picks are compatible with entry_type (tea/spell constraints)

### Acceptance criteria

- engine can produce a JournalPage for at least one scene/action
- locality works:
  - same_place used when available
  - same_zone used only when same_place insufficient
  - no silent widening beyond any_place unless explicitly configured
- journal output validates against journal_page.schema (frontmatter object)

---

## Milestone 4 — Domain engine v1 (step/choice loop)

### 4.1 Define core state model

File: `app/domain/state.py`

- PlayerState (Pydantic or dataclass):
  - session_id
  - current_place_id
  - inventory_counts: {item_id: qty}
  - flags: set[str]
  - visit_counts
  - seen_interactions
  - time_tick (optional)

### 4.2 Implement effects reducers

File: `app/domain/effects.py`

- apply_effects(state, effects) -> new_state
- validate inventory cannot go negative (unless allowed)

### 4.3 Implement action/scene selector

File: `app/domain/selector.py`

- eligible_actions(state, repo) -> list[Action]
- choose_action(actions, seed) -> Action

### 4.4 Implement Engine.step

File: `app/domain/engine.py`

Flow:

1) select eligible actions for current place/scene
2) resolve intent against eligible actions
3) apply chosen effects
4) render JournalPage
5) return StepResult:
   - journal_page
   - eligible_actions (next)
   - debug info

### Acceptance criteria

- step loop works end-to-end with deterministic seed
- applying a choice changes inventory/flags
- journal page reflects the step

---

## Milestone 5 — MongoDB persistence (runtime: sessions + state + journal history)

### 5.1 Mongo connection

File: `app/persistence/mongo.py`

- client init from env (MONGO_URI)
- db selection

### 5.2 Stores

File: `app/persistence/state_store.py`

- get_state(session_id)
- upsert_state(session_id, state)

File: `app/persistence/journal_store.py`

- append_page(session_id, journal_page)
- list_pages(session_id)
- get_page(session_id, page_id)

Optional:

File: `app/persistence/event_store.py`

- append_event(session_id, event)
- list_events(session_id)

### Collections

- `sessions`
- `state_snapshots`
- `journal_pages`
- (optional) `events`
- (optional) `content_versions` (pins a session to a content manifest hash/version)

### Acceptance criteria

- create session -> state persists
- step -> journal page appended
- reload -> state + pages match
- session data is portable across app restarts without reloading any content into Mongo
- (optional) a session can record the content manifest hash used to generate its pages

---

## Milestone 6 — FastAPI v1 (portfolio-facing)

### 6.1 App wiring

File: `app/main.py`

- FastAPI app
- dependency injection for repo + stores

### 6.2 Routers

File: `app/api/routers/sessions.py`

- POST /sessions
- GET /sessions/{id}
- POST /sessions/{id}/step

File: `app/api/routers/journal.py`

- GET /sessions/{id}/journal
- GET /sessions/{id}/journal/{page_id}

File: `app/api/routers/world.py`

- GET /world/places
- GET /world/npcs
- GET /world/items
- GET /world/scenes (optional, debug)
- GET /world/lexicons (optional, debug)

### 6.3 Services

File: `app/services/session_service.py`

- orchestrates:
  - load state
  - call engine
  - persist state
  - append journal page

### Acceptance criteria

- Swagger shows playable endpoints
- calling POST /sessions then POST /step returns a JournalPage + choices
- state persists across calls

---

## Milestone 7 — CLI v2 (later)

### CLI uses API

Files:

- `cli/main.py`
- `cli/render.py`
- `cli/client.py`

Flow:

- create/load session
- fetch last page
- print choices
- accept numeric input
- submit step

Acceptance criteria:

- playable loop from terminal
- identical journal artifacts

---

## Plan for Tomorrow's Work

## 1. Update API
- **Goal**: Extend the API to handle player-related operations.
- **Tasks**:
  - Implement an endpoint for creating new players.
  - Add functionality to save player progress and update player information as they move through the game.
  - Ensure all player data is written to MongoDB.
  - Write tests to validate the new endpoints.

## 2. Create a CLI for Game Interactions
- **Goal**: Build a command-line interface for interacting with the game.
- **Tasks**:
  - Use Typer to create the CLI.
  - Implement fuzzy matching for commands to improve user experience.
  - Add commands for starting the game, interacting with NPCs, and performing actions.
  - Write documentation for the CLI commands.

## 3. Update the SDK
- **Goal**: Enhance the SDK to support CRUD operations for game content.
- **Tasks**:
  - Add CRUD functionality for the following:
    - Scenes
    - Actions
    - Collectibles
    - Interactions
    - NPCs
    - Places
    - Spells
    - Tea
  - Ensure the SDK loads this content into memory efficiently.
  - Write unit tests for the new SDK functionality.
  - Update the SDK documentation to reflect the changes.

## General Notes
- Prioritize writing tests and documentation alongside implementation.
- Ensure all new features are integrated with existing systems and follow the project’s coding standards.

---

## Notes: “schema drift” policy (enforced)

- JSON Schemas validate JSON assets at load time.
- Pydantic models define API contracts and persistence shapes.
- Mongo stores runtime state and history; it is not a schema generator.
- Any “any:” token must either:
  - be resolvable by ingredient_substitutions.json (when used), or
  - be deferred with a clear TODO and a safe fallback path.
