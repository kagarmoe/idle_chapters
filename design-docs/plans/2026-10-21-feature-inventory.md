# Idle Chapters — Feature Inventory (design vs. implementation)

Audited 2026-10-21 on branch `worktree-swamp-quality-gates` (HEAD 2128d92). Read-only. Paths are relative to the repo root.

## How it runs today

There are **two separate games** that share no gameplay code.

1. **CLI: `python -m idle_chapters`** (`idle_chapters/main.py` → `scenes/welcome.py`, `scenes/cottage.py`)
   - Numeric menus. You pick or create a player (name and pronouns), then play a **hardcoded** cottage loop (`scenes/cottage.py:16-119`, `INTERACTIONS` list): rest, look around, make tea, pick up the journal, head to town.
   - It does **not** use the engine, `SessionService`, Mongo or `assets/actions.json`/scenes. Player data is saved as files in `assets/player.json`, `assets/players.json` and `assets/inventories/<id>.json`. These are git-tracked, not ignored.
   - "Head to town" prints a paragraph and the program **exits** (`cottage.py:244-246`, `run_cottage` returns).
   - Structured error projection with `-v/--verbose` works (Phase C).
   - `cottage.py:155-160` holds a dead `_load_tea()` that references undefined `state`/`player`. A second `_load_tea` at line 266 shadows it.
2. **API + web: `uvicorn idle_chapters.api.server:server`** plus `cd apps/web && npm run dev` → `http://localhost:5173/play/idle-chapters`
   - Needs MongoDB (`MONGO_URL`, default `mongodb://localhost:27017`; `MONGO_DB` default `idle_chapters`).
   - The web client finds the API through **`VITE_API_URL`** (`apps/web/src/lib/api.ts:106`). When it is unset it uses the same origin (`''`). No Vite proxy is configured, so local dev needs `VITE_API_URL=http://localhost:8000`. CORS defaults allow `localhost:5173,3000` and can be overridden with `CORS_ORIGINS`.
   - Endpoints the web client calls: `POST /v1/sessions` (New Game), `GET /v1/sessions/{id}` (Continue) and `POST /v1/sessions/{id}/action` (each choice). All requests send `Accept-Projection: player`. `api.ts` also wraps `/enter`, `/intent`, `/journal`, `/journal/{page}` and `/v1/world/*`, but the page **does not call them**.
   - Engine flow: `cottage_home` has an authored scene (`assets/scenes/cottage_wake_v1.json`, 6 nodes). Any place without an authored scene falls back to the procedural generator.
   - **Dead ends:**
     - (a) After `head_to_town` there are no choices: node `head_to_town` has `choices: []`, and the action has no `move_to` (`assets/actions.json`). The game stops.
     - (b) **Continue is broken.** `GET /v1/sessions/{id}` returns an empty `ViewModel()` (`api/routers/sessions.py:130`), so the resumed screen shows "A quiet moment. Nothing stirs." with no buttons. It should call `/enter`.
   - Tests: in a temp copy with Python 3.13, 150 passed and 25 skipped (Mongo-gated). 14 more failed or errored only because the copy changed the repo-root depth. `services/errors.py` and the CLI tests resolve `assets/` by a fixed parent depth, which is fragile. The worktree `.venv` has no pytest installed, and the system Python is 3.10, which lacks `StrEnum`. Use Python ≥3.11.

## Deployment notes from docs

- **Current plan:** `design-docs/plans/2026-03-17-deployment-design.md` (status "Approved")
  - Web: SvelteKit on **Vercel**, at kimberlygarmoe.com under `/play/idle-chapters`.
  - API: FastAPI on **Railway**.
  - Database: **MongoDB Atlas** free tier.
  - Repo: idle_chapters becomes a **git submodule** of `kagarmoe/kimberlygarmoe.com`.
  - Session ID is kept in localStorage. REST only.
- **Done:**
  - CORS env var (`api/server.py:18`).
  - `GET /health`.
  - `MONGO_URL`.
  - Root `Dockerfile` (uvicorn on port 8000).
  - Web pages and components.
  - CI: `.github/workflows/{api,web,docs}.yml`. The API CI runs a Mongo service and checks that the OpenAPI spec is fresh.
  - A swamp behavior `models/@swamp/vercel/projects/projects/idle-chapters-web.yaml` tracks a Vercel project named `idle-chapters` (current branch).
- **Not done:**
  - No Railway config.
  - No Atlas setup.
  - No submodule wiring.
  - `svelte.config.js` still uses `adapter-auto`.
  - `frontend_development.md` says "Not deployed. Local development only."
  - The plan's layout (`apps/api/`) was superseded by the package rename: the API is now at the repo root, and the Dockerfile copies `idle_chapters/ assets/ schemas/ lexicons/`.
- **Superseded:** AWS App Runner from GitHub (`implementation/drafts/game_design.md` §7, §9).
- **GitHub Pages** serves the OpenAPI docs and ReDoc from `docs/` (`docs/index.html`). `server.py:44-47` rewrites `docs/openapi.json` on every startup, including in production containers.
- **Open deployment risk:** the API's **default projection is `developer`** (`server.py:37`, commit 1bc483c). The design default was `player`. Any client that omits the header shows WHAT/MEANS/DO detail to players.

## Feature table

Status values: DONE, PARTIAL, NOT STARTED, SUPERSEDED. Size: S < 1 day, M = a few days, L = a week or more.

| ID | Feature | Source doc(s) | Status | Evidence | Notes/what's missing | Size |
|---|---|---|---|---|---|---|
| F01 | Content loading + JSON-schema validation at boot, in-memory `ContentRepo` + indices | V1_PLAYABLE_PLAN M1, ARCHITECTURE | DONE | `content/loader.py`, `content/repo.py`, `content/manifest.py` | Indices are built; most are unused by the engine (see F08, F14, F15) | – |
| F02 | Cross-file referential integrity checks | V1 M1.4 | PARTIAL | `content/validators.py`, `tests/content/test_validators.py` | **Never called** by `ContentRepo` or server startup. The plan says fail fast at boot. Wire one call | S |
| F03 | Authored scene graph + manifest (cottage first wake) | COTTAGE_STORYLET_GRAPH, SCENE_AND_ENGINE, SCHEMA_UPDATE | DONE | `assets/scenes/cottage_wake_v1.json`, `assets/scenes/manifest.json` | 3 scenes: cottage first wake, cottage homecoming (ic-13) and the town bakery (ic-15); V1 M2.5 targeted 6–10. Flag drift: doc says `left_cottage_once`, data has `left_cottage_first`. The graph doc says `make_tea` adds `chamomile_flower`; data has `chamomile_flowers` | M |
| F04 | Global reusable action catalog with `when` gating | SCENE_AND_ENGINE, SCHEMA_UPDATE | DONE | `assets/actions.json` (6 actions), `schemas/actions.schema.json` | All 6 are cottage-only | – |
| F05 | Declarative conditions (location, zone, flags, inventory, visits, seen, day) | SCENE_AND_ENGINE, SCHEMA_UPDATE, overview draft | DONE | `domain/conditions.py`, `tests/domain/test_conditions.py` | `time_of_day` is skipped (`conditions.py:53`). No cooldown, once-per-day or mutual-exclusion rules | S |
| F06 | Effect reducers (add/remove items, flags, move) | ARCHITECTURE, SCENE_AND_ENGINE | PARTIAL | `domain/effects.py` | No `time.advance`. `move_to` counts an arrival in `visit_counts` (ic-4); no seen-interaction updates. No action uses `move_to`. `RANDOM_CHOICE` and mood effects (overview draft) are absent | S |
| F07 | Engine.step → StepResult (journal_page, choices, state, debug) | ARCHITECTURE, overview draft, V1 M4 | DONE | `domain/engine.py`, `domain/step_result.py`, `tests/domain/test_engine.py` | Debug metadata is thin: no `eligible_count` or `applied_effects` ("Observability" in ARCHITECTURE) | S |
| F08 | NPC interaction system (5 structural types: ambient, micro-offer, ritual, light request, threshold) | interactions_design, V1 M2.3 | NOT STARTED (data only) | `assets/interactions.json` (60), `assets/npcs.json` (23), indexed in `repo.py:95-114` | The engine never reads interactions. No NPCs ever surface in play. This is the largest gap between design and runtime | L |
| F09 | NPC visibility / social_level selection, `visible_npcs`, `visible_items` in the view | SCENE_AND_ENGINE, SCHEMA_UPDATE, CLI_INTENT_PARSING | NOT STARTED | `api/routers/sessions.py:37-47` never sets them, so `InventoryPanel` is always empty | Needs F08 | M |
| F10 | NPC address rules (optional vocatives, frequency styles, fixed pools) | interactions_design §3 | NOT STARTED | Pronouns are collected by the CLI (`welcome.py:101`) and `/v1/players` | No dialogue uses them | M |
| F11 | Premise facets → interaction bias (`pause_is_valid`, `time_is_soft`, `between_lives`, `stay_is_normal`) | interactions_design §4, players_design | NOT STARTED | `assets/player.json` premise has `creativity`/`empathy` facets, which don't match the design | Decide the facet set first | M |
| F12 | Journal page as primary output (frontmatter + markdown body) | ARCHITECTURE, storylets_design, sample_journal_page | DONE (basic) | `domain/journal_renderer.py`, `assets/journal_templates.json` (4: tea, spell, field_note, inventory) | Prose is canned keyword lines (`_render_section`). No lexicon use. `page_id` is an md5 of place+type+epoch-seconds, so pages can collide within the same second. The `inventory` template is unreachable (`_infer_entry_type` never returns it) | M |
| F13 | Ingredient picking with locality (same_place > same_zone > any) + `any:` substitutions | V1 M3.3 | DONE | `domain/ingredient_picker.py`, `assets/ingredient_substitutions.json`, tests in `tests/journal/` | Picks are cosmetic; inventory is not consumed | – |
| F14 | Tea recipes / tea ritual | game_constructs draft, storylets_design | PARTIAL | `assets/tea.json` (4); CLI renders the first matching recipe (`cottage.py:201`); `repo.tea_by_id` is unused by the engine | No engine "make tea from recipe" action that consumes ingredients | M |
| F15 | Spells / portal (thin places, mirror + crystal, incantations) | game_constructs draft, V1 M2.3 | NOT STARTED (data only) | `assets/spells.json` (1: `portal_homeward`), `prompts_ai/incantation_prompt.md`; threshold places set `entry_type=spell` for actions without a `move_to` effect; arrivals get `tea` pages since ic-12 | No cast action, prerequisites or portal travel | L |
| F16 | Notebook (lists tea, spells, snacks, meals; can't be lost) | game_constructs draft | NOT STARTED | – | Overlaps the journal; needs a design decision | M |
| F17 | Energy / mood stats (naps, snacks restore energy) | game_constructs draft, overview draft (`STAT_GTE`, `ADD_MOOD`) | NOT STARTED | – | **Tone risk** (see below). Probably drop it | – |
| F18 | Soft time: time-of-day by action, days, seasons, weather | game_constructs draft, players_design §4, procedural_generation | NOT STARTED | `time_tick` exists in state and persistence but is never advanced | Interaction conditions already carry time_of_day, weather and season fields | M |
| F19 | Visit counts, seen interactions, cooldowns, variety (avoid repeats) | SCHEMA_UPDATE, SCENE_AND_ENGINE | PARTIAL | Fields in `domain/state.py`, persisted in `persistence/state_store.py`, evaluated in conditions | Visit counts count arrivals (ic-4: start place 1, +1 per `move_to` to a new place). Seen interactions move to P1 #8; cooldowns and variety not started | S |
| F20 | `result_variants` (seeded, non-escalating repetition) | SCENE_AND_ENGINE, CLI_INTENT_PARSING | PARTIAL | `journal_renderer.py:151` uses `variants[0]` | No action defines variants. No seeded pick | S |
| F21 | World map: 5 zones / 17 places, travel between them | ARCHITECTURE, places schema | DONE | `assets/places.json`, path actions in `assets/actions.json`, `Engine._with_paths` | ic-5: paths connect the cottage, town and the forest, meadow and beach zone roots, and are offered at every step. ic-12: each zone root leads into its three sub-places (`town_bakery` etc.), and each sub-place leads back to its root or home. Zone roots and sub-places get procedural scenes | M |
| F22 | Procedural scene generator (families, lexicon-safe prompt, 3 choices, seeded, debug) | V1 M2.3, procedural_generation, overview draft | PARTIAL | `domain/scene_generator.py`, `domain/selector.py:generate_candidates`, `tests/domain/test_scene_generation.py` | Output is "`<word>` lingers nearby." plus 3 no-op labels; choosing one just re-rolls (`engine.py:95-99`). The plan wanted interaction-shaped output validated against `interactions.schema.json`. `merge_with_authored` exists but is unused | M |
| F23 | Generator patterns: daily pre-fill, lazy fallback, template expansion, Ambient/DailyMood generators | procedural_generation, overview draft | PARTIAL | Lazy fallback only (`engine.py:63-81`) | Others not started | M |
| F24 | Tone enforcement by lexicons (Not_Allowed filter, sensory words, need-weighted bias) | tone_contract §5–6, ARCHITECTURE | PARTIAL | `lexicons/*.json` (44 descriptive, 17 not-allowed); the generator filters (`scene_generator.py:28-52`); `tests/content/test_error_templates.py` checks templates | Authored action text and journal prose are not checked. No soft weighting toward `player_need_satisfied` | M |
| F25 | Freeform intent parsing via `intent_signature` (keywords/phrases, multi-intent "and/then", phrase > keyword) | CLI_INTENT_PARSING, SCHEMA_UPDATE, ARCHITECTURE ("no numeric menus") | PARTIAL | `POST /v1/sessions/{id}/intent` → `session_service._match_intent` (`:260`) does a **label substring** match only | `intent_signature` data in `actions.json` is unused. No multi-intent. `submit_intent` calls `enter` first, which re-rolls the scene | M |
| F26 | Out-of-world meta commands ("What can I do?", "What is here?", "Help") | CLI_INTENT_PARSING | NOT STARTED | – | – | S |
| F27 | CLI as a client of the API / SessionService (M7) | ARCHITECTURE, V1 M7, m6 design (M6→M7 contract) | NOT STARTED | The current CLI is a separate hardcoded game (see "How it runs today") | Replace `scenes/cottage.py` with a loop over `SessionService`. That would remove duplicated content and file persistence | M |
| F28 | Typer CLI with fuzzy matching; NPC commands | V1 "Plan for Tomorrow" | NOT STARTED | argparse only (`main.py:25`) | Overlaps F25/F27 | M |
| F29 | Local file player profiles (CLI) | (none; organic) | DONE but off-design | `scenes/welcome.py`, `assets/players.json`, `assets/inventories/*.json` | Writes runtime data into `assets/`, which the docs treat as read-only content. Committed to git | S |
| F30 | Sessions API: create/get/enter/action/intent/journal list/page | ARCHITECTURE, API_DESIGN, m6 design | DONE | `api/routers/sessions.py`, `services/session_service.py`, `tests/api/test_api.py` | `GET` returns an empty view (breaks Continue). `/step` was renamed to `/action`, `/enter` and `/intent` (m6 decision) | S |
| F31 | `/peek` and `/sessions/{id}/events` endpoints | API_DESIGN, ARCHITECTURE (optional) | NOT STARTED | `EventStore.list_events` exists with no route | – | S |
| F32 | World read-only endpoints | ARCHITECTURE, API_DESIGN | DONE | `api/routers/world.py` (manifest, places, scenes, actions, collectibles, npcs) | `/world/recipes` (tea/spells), `/world/lexicons` and `/world/interactions` are missing | S |
| F33 | Players API (create/get/patch, inventory, journal) | API_DESIGN, V1 "tomorrow" | PARTIAL | `api/routers/players.py`, `api/routers/journal.py` | **Players aren't linked to sessions**: `SessionCreateRequest` has only `place_id`. `/players/{id}/journal` and `/inventory` read data that is never written, so they always return empty | M |
| F34 | Determinism: seed anchored to session/state; no re-roll on reconnect | API_DESIGN decision 1, procedural_generation ("same day feels the same") | PARTIAL | The engine accepts `seed`; `SessionService` **never passes one** (`session_service.py:48,62,76`) | Each `/enter` re-randomizes | S |
| F35 | Mongo persistence: state snapshots, journal pages (append-only), event log | V1 M5, m5 design | DONE | `persistence/{mongo,state_store,journal_store,event_store}.py`, `tests/persistence/` (skipped without `MONGO_URL`) | Two Mongo singletons duplicate each other (`api/db.py` and `persistence/mongo.py`) | – |
| F36 | Content-version pinning per session (manifest hash) | V1 M5 (optional) | NOT STARTED | – | – | S |
| F37 | Session TTL / cleanup | API_DESIGN tradeoffs | NOT STARTED | – | Needed before a public deploy on the Atlas free tier | S |
| F38 | MongoContentProvider / live content editing | V1 M1.3 (future) | NOT STARTED | – | Explicitly deferred; YAGNI | – |
| F39 | Structured errors: domain exceptions → GameError → projections, RFC 9457 + Z535 | errors.md, structured-errors design/plan, CLI plan | DONE (Phases A, B, C) | `domain/errors.py`, `services/errors.py`, `assets/error_templates.json` (10 kinds), `ui/errors.py`, `api/server.py:35-42` | **Agent projection** is not started. The default projection flipped to developer | S |
| F40 | OpenAPI as first-class artifact, examples on every route | api-docs design/plan, game_design draft §8 | DONE | `api/models.py` `json_schema_extra`, `api/routers/error_helpers.py`, `docs/openapi.json`, `tests/api/test_example_accuracy.py` | – | – |
| F41 | Spec-first codegen (`openapi-generator` → `app_generated/`) | API_GENERATION.md | SUPERSEDED | Code-first: the spec is exported at startup and checked in CI | Delete or mark the doc as superseded | – |
| F42 | GitHub Pages API docs (ReDoc) | docs-reorganization | DONE | `docs/index.html`, `.github/workflows/docs.yml` | – | – |
| F43 | Observability: domain events, OpenTelemetry, analytics/event-summary endpoints | game_design draft §8, API §7, ARCHITECTURE | PARTIAL | `EventStore` writes `step` events; `telemetry.py:init_otel` is **never called** | No analytics endpoints | M |
| F44 | Web client: splash (ASCII art), typewriter + click-to-skip, choice bar, journal card, inventory panel, localStorage resume | deployment design, frontend_development.md | PARTIAL | `apps/web/src/lib/*.svelte`, `routes/play/idle-chapters/+page.svelte` | Missing: **free-text input**, scrollable **journal history** (only the latest page shows), inventory data, a working Continue, and an end-of-scene state. The journal card shows "Untitled" and repeats the prompt text, because the view prompt is the journal body. The raw `scene_id` is shown to players | M |
| F45 | Personal-site shell (/, /projects, /writing, /data, /thinking, /play) | deployment design | DONE (stubs) | `apps/web/src/routes/*` | Content is intentionally stubbed | – |
| F46 | Tone system prompt + prompt library + coverage test | tone-system-prompt plan, llm_generation draft | DONE | `prompts_ai/tone_system_prompt.md` + 7 prompts, `tests/test_tone_prompt_coverage.py` | – | – |
| F47 | Runtime LLM generator behind a generator interface (sanitized state, no engine access) | llm_generation draft, overview draft | NOT STARTED | Only offline `utilities/chatgpt_query.py` (OpenAI gpt-4o-mini) and `utilities/backfill_assets.py` for filling asset fields | – | L |
| F48 | Asset maintenance utilities (schema backfill, update) | utilities/README | DONE | `utilities/update_assets.py`, `backfill_assets.py`, `tests/assets/` | – | – |
| F49 | Content CRUD "SDK" | V1 "tomorrow" | NOT STARTED | `utilities/sdk.py` is a ~20-line validator | Probably unneeded | M |
| F50 | Player writing: fill-in prompts, leave notes in places, journaling | sample_journal_page, game_constructs `write`, players_design §6 | NOT STARTED | The journal page body has no blanks; no write endpoint | Needs the observational, not confessional, constraint | M |
| F51 | Other verbs: nap, snack, meal, pet, talk, wander, float, pickup/seek, shop | game_constructs draft, game_design draft | NOT STARTED | – | Shop/money conflicts with ARCHITECTURE non-goals | L |
| F52 | Relationships / affinity | ARCHITECTURE (optional, later), npcs/interactions `affinity` | NOT STARTED | Schema fields only | Must not escalate as a reward (interactions_design §3.3) | M |
| F53 | Deployment (Vercel + Railway + Atlas, submodule) | deployment design | PARTIAL | See "Deployment notes" | Hosting, adapter, secrets and the Railway service | M |
| F54 | CI (API pytest + Mongo, web check/build, docs) | deployment design, CLAUDE.md | DONE | `.github/workflows/*.yml` | The CLAUDE.md gates list Next.js/npm commands (`auth:verify`, `test:db`) that don't exist in this repo | S |
| F55 | Package rename `app` → `idle_chapters`, flat tests | package-rename design/plan | DONE | `idle_chapters/`, `tests/<mirrored>/`, `__main__.py` | – | – |
| F56 | Docs reorganization (`docs/` = Pages only) | docs-reorganization design/plan | DONE | No `dev-docs/`; plans are in `design-docs/plans/` | – | – |
| F57 | Swamp quality-gate behaviors (current branch) | (none in design-docs) | IN PROGRESS | `extensions/behaviors/idle_chapters_checks.ts`, `models/@kagarmoe/idle-chapters-checks/` | – | S |
| F58 | Accessibility audit, offline/service worker | frontend_development.md | NOT STARTED | Typewriter uses a click-only skip (`a11y_click_events_have_key_events` is suppressed) | – | S |

## Plans status

| Plan file | Status | Evidence |
|---|---|---|
| `implementation/V1_PLAYABLE_PLAN.md` | **Partial** | M0–M6 done with gaps: M2 has 3 scenes, not 6–10, and the generator isn't interaction-shaped; M1.4 validators aren't wired. M7 (CLI over the API) is not done. The "Plan for Tomorrow" section (players API, Typer CLI, SDK) is only partly done (players API) |
| `plans/2026-02-27-m5-persistence-design.md` + `-plan.md` | Executed | `idle_chapters/persistence/*`, `tests/persistence/test_persistence.py` |
| `plans/2026-02-27-m6-fastapi-design.md` + `-plan.md` | Executed | `services/session_service.py`, `api/routers/sessions.py`, `api/deps.py` |
| `plans/2026-03-17-deployment-design.md` | Partial | Backend prep and web UI done; nothing hosted; no submodule or Railway |
| `plans/2026-04-04-docs-reorganization-design.md` + `-plan.md` | Executed | `docs/index.html`, `docs.yml`, no `dev-docs/` |
| `plans/2026-04-04-package-rename-design.md` + `-plan.md` | Executed | `idle_chapters/`, root `Dockerfile`/`pyproject.toml` |
| `plans/2026-04-04-api-docs-design.md` + `-plan.md` | Executed | PR #49, `docs/openapi.json` |
| `plans/2026-04-04-structured-errors-design.md` + `-plan.md` (Phase A) | Executed | PR #47; Phase B in PR #48 |
| `plans/2026-07-06-structured-errors-cli-plan.md` (Phase C) | Executed | PR #56 (checkboxes left unticked). The agent projection is still future |
| `plans/2026-04-04-tone-system-prompt.md` | Executed | `prompts_ai/tone_system_prompt.md`, `tests/test_tone_prompt_coverage.py` |

There is no plan at all for the core gameplay gaps: NPC interactions, travel and town, tea/spell mechanics, time, or player writing. The last design work was on errors, docs and tooling (April–July). Gameplay has been static since roughly M4 (Feb 2026).

## Stale or contradictory docs

- `implementation/frontend_development.md` says errors are hardcoded in the Svelte component. This was fixed: the page now uses `problemDetail.title`.
- `errors.md` and the structured-errors design say the default projection is `player`. The code defaults to `developer`.
- `ARCHITECTURE.md` says "no graphical UI", "CLI is a client of the API" and "no numeric menus". Reality: a web UI exists, and the CLI is standalone with numeric menus.
- `storylets_design.md` refers to `*.yaml` assets, `dev/` and `generators/` directories. Reality: JSON assets, `design-docs/` and `domain/`.
- `API_GENERATION.md` (spec-first) is superseded by code-first.
- `game_design.md` draft: AWS App Runner is superseded by Vercel/Railway.

## Tone-contract risks

1. **Energy stat** (game_constructs draft: "restore their energy… the game is basically about feeling better"; wander "Requirements: Energy"). This is resource management and conflicts with players_design §3/§7 (no recovery tracking, "rest is not remediation"). Recommend dropping it.
2. **"There's no bed-rotting in idle_chapters"** and "the day doesn't advance until you leave the house" (game_constructs draft). This judges rest and contradicts "Pause is a valid mode" and "you are allowed to be where you are".
3. **Location "immediacy" spending:** you must revisit a place before reusing it in a spell. This is a scarcity/obligation mechanic (tone_contract §3: resource anxiety).
4. **Shop "spends money"** (game_constructs). Scarcity and economy; ARCHITECTURE lists "no complex economy" as a non-goal.
5. **Consuming ingredients** on tea/spell (`inventory.use`) and `remove_items` raising `InsufficientInventory`. This is fine only if key items stay bountiful (cozy_games.md). The `insufficient_inventory` template ("This would take {required}. Maybe you'll find more…") foregrounds a deficit.
6. **Spell prerequisites** ("requires that the player is at the top of the forest waterfall and has a mirror and a crystal"). Keep them optional and non-instructional (interactions_design §2.4).
7. **Mood effects** like `ADD_MOOD("restless")` and `ADD_MOOD("wistful")` (overview draft). "Restless" is outside the allowed emotional range.
8. **NPC affinity / light requests:** these can drift into obligation or reward escalation. The design guards against it, but there is no implementation yet to check.
9. **Developer projection as the API default:** a careless client would show "WHAT/MEANS/DO… Report this to a developer" to players.
10. **Minor UI copy:**
    - The web fallback "Something went quiet ({status})" shows an HTTP status to players.
    - The raw `scene_id` label (e.g. `COTTAGE_WAKE_V1`) breaks immersion.
    - The plan calls click-to-skip a feature "for impatient players".
    - `session_not_found` ("That story has found its own ending") hints at irreversible loss.
11. **NPC `npc_watchman_bened`:** the "watchman" role connotes vigilance or authority (tone_contract §5.4). The notes soften it ("stands quietly at the view").
