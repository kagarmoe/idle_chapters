# idle_chapters — Design Decisions

Idle Chapters values:

- Calm
- Low stakes
- Coherence
- Psychological safety

To achive this, I'll use:

- Narrow vocabularies
- Low entropy
- Few surprising effects
- Strong engine gating

## About the game

Session model: **Single-player, persistent save** (player resumes over days)
    - Single-player, ephemeral run (roguelike-ish, deletes after run)
Game loop: Hybrid, emphasizes choice-based storylets but will also have some commands.
Determinism: The ititial version is mostly deterministic. RNG for ambiance or small things.

## Python Design

### Model: domain objects + rules (pure Python)

- GameState, Player, Inventory, Location, Storylet, Effect, Condition
- A GameEngine that applies commands to state

### View: API response schemas (Pydantic) + optional UI later

- “View” is basically: DTOs, serialization, and presentation strings

### Controller: FastAPI route functions

- Very thin: validate input → call service → return DTO

### Handlers (the important part for text games)

- Command/intent handlers: handle_look, handle_move, handle_use
- Each handler calls domain logic and emits:
- state changes (events/effects)
- “renderable” text output (or message tokens)

### Game state stores

- Snapshot: one JSON blob per save (simple, fast to build)
- Event sourcing: store events, rebuild state (excellent for audits/debugging)
- Hybrid: snapshots + events since last snapshot (best-of-both)

## Stack

- FastAPI + Pydantic schemas
- Domain engine with command handlers (pure Python)
- Store static content in repo (YAML/JSON)
- MongoDB for save-state snapshots (one doc per session) or MySQL if you want migrations
- POST /sessions/{id}/commands as the main loop endpoint
- Structured logging + OpenTelemetry + Dashboard

## Notes

1. Core Concept

   - idle_chapters is a cozy, text-based RPG about nothing much at all.
   - The experience is intentionally low-stakes, ambient, and reflective.
   - Progress is measured in moments and fragments.
   - The project is API-first and narrative-driven.

2. Scope & Intent

  It is a narrative system that demonstrates:
     - state management
     - conditional content selection
     - modular storytelling
     - observability applied to meaningful domain events
  The design prioritizes clarity, restraint, and extensibility over features.

1. Gameplay Model (High-Level)

  The game operates as a state + content selector:
  Given a small current player state, the system selects an appropriate narrative fragment.
      - The fragment may gently alter state, or simply be observed.
      - Many interactions are ambient rather than player-driven.
      - Player “actions” (if present) are verbs like rest, wander, or read
      - Player actions are not tactical commands.

1. Narrative Structure

  There is no required overarching plot, meaning emerges through accumulation.
  The primary narrative unit is a storylet:
     - A small, self-contained piece of prose.
     -  May have simple conditions (location, inventory, mood, flags).
     -  May have simple effects (state changes, flags, item acquisition).
  Storylets are:
    - modular
    - reusable
    - non-linear

1. State Design Philosophy

  State exists to shape context, not to enforce progression or challenge.
Player state is intentionally minimal.

  Likely elements include:
     - current location
     - inventory (small, meaningful items)
     - mood or tone
     - lightweight flags indicating past encounters

1. World Modeling

   - Locations are containers for tone and potential moments, not puzzles.
   - Items are often narrative or atmospheric rather than mechanical.
   - Systems are designed so that new content can be added without changing core logic.

2. Technical Framing

   - The backend will be a FastAPI application.
   - The API exposes:
     - narrative content
     - state transitions
     - event triggering
     - simple analytics endpoints
   - OpenAPI documentation is treated as a first-class artifact.
   - The app is intended to deploy on AWS App Runner, sourced from GitHub.

3. Observability as a Design Feature

   - Events are logged intentionally, such as:
     - storylets triggered
     - locations visited
     - actions taken
   - Observability is framed as:
     - understanding which moments occur
     - how often
     - under what conditions
   - Metrics and logs support both technical monitoring and narrative insight.

4. Naming & Positioning

   - The project name is idle_chapters.
   - The name emphasizes:
     - episodic structure
     - gentle pacing
     - non-urgent progression
   - It clearly signals “game” while remaining understated and literary.

## idle_chapters — API Design Decisions

1. API-First Architecture

   - idle_chapters is designed as an API-first system.
   - The API is the authoritative interface for:
     - game state
     - narrative content
     - event progression
     - observability data
   - No client (CLI, web UI, etc.) is required to understand or validate the system.

2. RESTful, Resource-Oriented Design

   - The API models the domain as explicit resources, not commands.
   - Core resources include:
     - players (or sessions)
     - locations
     - storylets
     - items
     - events / invocations
   - Interactions are expressed as:
     - resource creation
     - state transitions
     - content retrieval

3. Clear Separation of Concerns

   - Content is treated as data:
     - storylets, locations, items are authored independently.
   - State is treated as context:
     - player/session state is minimal and mutable.
   - Logic is limited to:
     - selecting valid content
     - applying small, explicit state changes
   - The API does not embed a scripting engine or complex rules engine.

4. Storylets as First-Class API Objects

   - Storylets are the primary narrative unit exposed by the API.
   - Each storylet:
     - is addressable via an ID
     - may include optional conditions and effects
   - The API supports:
     - listing storylets
     - retrieving individual storylets
     - selecting a storylet based on current state
   - Narrative progression is emergent, not linear.

5. State-Driven Interaction Model

   - API calls operate against a current player or session state.
   - The API:
     - accepts state as input
     - returns narrative output
     - may return updated state
   - State transitions are explicit and observable.
   - There is no hidden server-side “game loop.”

6. Minimal, Intentional Actions

   - Player actions are few and generic (e.g., rest, wander, read).
   - Actions act as triggers rather than complex commands.
   - The API remains readable without game-specific jargon.

7. Observability Is Part of the API Surface

   - Narrative events (storylet triggers, actions, state changes) are logged as domain events, not just HTTP requests.
   - The API exposes endpoints for:
     - basic analytics
     - event summaries
     - usage patterns
   - Observability is designed to explain what happens in the game, not just whether the service is healthy.

8. OpenAPI as a First-Class Artifact

   - OpenAPI documentation is considered part of the product.
   - Endpoint naming, schemas, and responses are designed to:
     - read clearly in Swagger / ReDoc
     - tell a coherent story about the system
   - The API is self-describing and explorable without additional tooling.

9. Deployment-Friendly Design

   - The API is built to run as a single FastAPI service.
     - exposes a single HTTP port
     - has no hard dependency on a specific client
   - The design aligns cleanly with AWS App Runner deployment from GitHub.

10. Explicit Non-Goals

- The API does not:
- implement real-time gameplay
- require authentication complexity in v1
- include multiplayer or concurrency mechanics
- embed business logic in the client
- Complexity is deferred intentionally to preserve clarity.
