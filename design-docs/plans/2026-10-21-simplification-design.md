# Simplifying the repository — audit and plan (for review)

**Status: proposed, not started.** Written overnight 2026-10-21 for the owner to review. Each
phase is one PR. Items marked **Decide** need the owner; the rest are my recommendation.

The owner asked:
- Why are there both `idle_chapters/` and `apps/web/`, and can they be consolidated?
- Can things be simplified or consolidated more generally?

The evidence comes from a read-only audit of the tree: imports, CI, the swamp workflows, and
last-touched dates. I spot-checked the claims that matter.

## The short answer about `idle_chapters/` and `apps/web/`

They are not duplicates, and I recommend **not** moving either one:

- **`apps/web/`** is only the browser client (SvelteKit, about 1.2k lines), served as Vercel's
  `web` service.
- **`idle_chapters/`** is the Python package (about 4.3k lines). It holds the FastAPI API that
  Vercel serves as the `api` service, plus the game engine, content loading and persistence.
  It also holds a **second, older game**: the terminal version (`python -m idle_chapters`:
  `main.py`, `scenes/`, `ui/`, about 690 lines and about 23 tests). That game runs its own loop
  and doesn't use the engine at all.
- The package used to live at `apps/api/app/`. It was moved to the root **on purpose** on
  2026-04-04 (`2026-04-04-package-rename-design.md`: the nesting "adds unnecessary depth and
  requires PYTHONPATH manipulation"). Moving it back would undo that decision. It would also
  touch:
  - `vercel.json` and `pyproject.toml`;
  - how assets are found and bundled, and three hand-rolled parent walks;
  - pytest config and a repo-structure test;
  - CI path filters and the swamp `validateAssets` step;
  - the OpenAPI writer, the Dockerfile and the README.

  That's a lot of risk for a tidier-looking tree.

What does make the tree simpler is **retiring the terminal game** (Phase 3). The package would
then be only what the website uses.

## Found along the way: a live bug (do this first)

**Players lose the written error messages in production** (bead `chapters-00w`).

- `services/errors.py:_find_repo_root` looks for a `.git` *directory*. Vercel has none, and in
  a worktree `.git` is a file.
- It then falls back to `parents[3]`, one level *above* the repo, so `error_templates.json` is
  never found and every message falls back to generic text.
- Verified 2026-10-22: `GET /v1/sessions/probe-missing` with `Accept-Projection: player`
  returns "Something unexpected happened." The intended line is "That story has found its own
  ending. You're welcome to begin a new one whenever you'd like."
- **Fix:** find the root the way `ContentRepo` already does (the folder holding `assets/` and
  `schemas/`), share that one helper, and add a regression test that the templates load.
  `ContentRepo`'s own fallback (`parents[4]`) is also a stale depth; drop it.
- **Phase 0, one small PR.**

## Phase 1 — delete what nothing uses (low risk, no decisions)

| Remove | Evidence |
|---|---|
| `drafts/` (5 files) | Nothing references it. Four files are byte-identical to `assets/`/`schemas/`. The fifth is an older copy (`Botanical` vs the live `botanical`). |
| `idle_chapters/telemetry.py` | Imported by nothing. The monitoring work chose logs over tracing. |
| `Dockerfile` | Left from the Railway plan; nothing builds it. |
| `schemas/error_response.schema.json` | Referenced by nothing. |
| Manifest entries for `sessions` and `journal_page` schemas | ContentRepo never loads them. Keep the journal schema file if its test stays. |
| `models/@swamp/vercel/projects/env/vite-api-url.yaml` | Describes itself as "Retired". Delete the stale Vercel variable it manages first, then the model, then the `VITE_API_URL` guard in `playwright.config.ts`. |
| Unused Python packages in `requirements.txt` (about 20) | numpy, pyarrow, pylance, lance-namespace, the opentelemetry set, typer/rich/click/shellingham, PyYAML, dateutil, pytz. Nothing in the API, engine or tests imports them. Confirm with a clean install and a test run in the PR. |
| `pytest.ini` `env =` lines | Need `pytest-env`, which isn't installed, so they do nothing. |
| `apps/web/README.md` | Untouched `sv create` boilerplate. Replace it with three lines (how to run, where the API is) or delete it. |

## Phase 2 — one source of truth for docs and agent instructions

- **AGENTS.md and CLAUDE.md** repeat the knowledge map, the beads quick reference, the rules
  and session completion almost word for word.
  - Keep the shared text in `AGENTS.md`. Have `CLAUDE.md` pull it in with an `@AGENTS.md`
    import, keeping only Claude-specific lines plus swamp's managed section.
  - **Decide:** is AGENTS.md read by any other agent you use? If not, fold everything into
    CLAUDE.md instead.
- **Design docs** are 48 files, about 11.2k lines.
  - About 6k lines are executed plans (m5/m6/rename/docs/structured-errors pairs) and
    `implementation/drafts/`. Move them to `design-docs/archive/`. They stay findable but stop
    reading as current.
  - Six live docs contradict the code. They are already listed in
    `2026-10-21-feature-inventory.md`: ARCHITECTURE (no GUI, CLI is an API client),
    storylets_design (yaml, `dev/`), API_GENERATION (spec-first), frontend_development,
    errors (default projection), and 2026-03-17-deployment (Railway).
  - Fix or archive each one. The storylet doc can wait for the content-authoring decision
    (`2026-10-21-content-authoring-design.md`), which will rewrite it anyway.
- **Stale `dev/game_design` paths** in `utilities/` and five docs point at the old location of
  `tone_contract.md`.

## Phase 3 — retire the terminal game (Decide: the biggest single simplification)

- **Remove:**
  - `idle_chapters/main.py`, `__main__.py`, `scenes/` (cottage, welcome, inventory) and `ui/`;
  - their tests: `tests/player/*`, `tests/ui/test_cli_errors.py`, `test_cli_args`;
  - the CLI's save files committed in `assets/` (`player.json`, `players.json`,
    `inventories/*.json`), which the API never reads;
  - the README's "Play in the terminal" section.
- **Keep** `domain/intent.py`, which the API uses too.
- **Why:** it is a second game loop that the engine and website don't share. The content
  authoring work will otherwise have to keep both games in step. (Its prose is hard-coded in
  `scenes/cottage.py`.)
- **Decide:** do you still play or demo the terminal version? If yes, the alternative is a thin
  CLI client of the API, as ARCHITECTURE.md always intended. That is a project, not a cleanup.

## Phase 4 — `utilities/` (Decide)

- `sdk.py` is a Typer demo that nothing imports.
- `chatgpt_query.py` and `backfill_assets.py` call OpenAI through `requests`, read a stale
  tone-contract path (so backfill silently runs with an empty tone contract), and only their
  tests use them.
- `update_assets.py` fills in fields after a schema change. That's still useful while schemas
  change.
- **Recommendation:** delete everything except `update_assets.py` and its test.
- **Decide:** do you still want AI backfill of blank fields? If yes, rebuild it later on
  `@keeb/anthropic` (below), not on the old OpenAI script.

## Phase 5 — one definition of "the checks" (medium risk)

Today the gates are defined three times:
1. GitHub Actions: pytest with Mongo, the OpenAPI drift check, svelte check/build/e2e, docs.
2. swamp `ic-checks`: validate-assets, pytest, build, e2e. It has no OpenAPI drift or docs
   check.
3. The stagecraft factory's checks stage.

Recommendation:
- Make swamp `ic-checks` the complete list. Add the OpenAPI drift check and `svelte-check`.
- Have GitHub Actions run the same commands, keeping its Mongo service.
- Drop the double web build: e2e's Playwright `webServer` already builds, so `build-web`
  followed by `e2e-web` builds twice.

**Decide** whether GitHub Actions should call swamp directly. It would need swamp installed in
CI, a heavier but truly single source.

## Phase 6 (optional) — group the content folders

If the tree still feels busy after phases 1–4, move `assets/`, `schemas/`, `lexicons/` and
`prompts_ai/` under one `content/` folder.
- **Touches:** the manifest, the shared root helper from Phase 0, and tests.
- **Timing:** it pairs naturally with content authoring, which will add folders there anyway.
  Skip it unless that work wants it.

## Tooling: extensions worth adopting

I surveyed @maphew, @keeb and @swamp (668 extensions; most of @swamp's are cloud providers and
most of @keeb's are home-lab and media). Relevant here:

| Extension | Use here | Status |
|---|---|---|
| `@maphew/housekeeping` | Dev-environment hygiene: repo, worktrees, temp files, stale bead claims. | **Adopted tonight**: `ic-tidy` workflow + our `pruneMergedBranches` (PR #103). |
| `@keeb/discord` | Swamp's posts to Discord. | Adopted (`ic-alerts`, `ic-ship`). |
| `@maphew/handoff` | "Exact-state handoffs: Git + Bead snapshot, narrative, resume brief". | **Try it** to replace the hand-kept `HANDOFF.md`. |
| `@maphew/repo-doctor` | Hard-coded home paths, extension integrity, gitignore checks. | **Try it**: it would have caught the stale `dev/` paths. Could be an `ic-tidy` step. |
| `@maphew/agent-config` | Inventory and drift check of AI-tool config. | Fits Phase 2 (AGENTS.md/CLAUDE.md drift). Optional. |
| `@keeb/github` | Lists PRs via `gh`. | Optional: `pruneMergedBranches` could read PRs from its data instead of calling `gh` itself (swamp rule 3, "use the data model"). |
| `@keeb/ports` | Listening ports with process/project, plus cleanup of orphaned ones. | Optional: catches leftover vite/uvicorn dev servers. A natural `ic-tidy` step. |
| `@keeb/anthropic` | Generate text with Claude from workflows. | For content authoring: a tone-contract §10 check on hand-written prose, which nothing checks today. |
| `@keeb/mongodb`, `@keeb/mongodb-stats` | MongoDB inspection. | Optional, if production persistence needs looking at. |
| `@keeb/skill-converter` | Turns Claude Code skills into swamp workflows. | Not needed now. |

## Suggested order

| Phase | What | Risk | Waits on |
|---|---|---|---|
| 0 | Error-templates bug | low | nothing |
| 1 | Delete the unused | low | nothing |
| 2 | Agent docs + design-docs archive | low | AGENTS.md question |
| 3 | Retire the terminal game | medium | owner decision |
| 4 | `utilities/` | low | owner decision |
| 5 | One set of checks | medium | GitHub Actions/swamp question |
| 6 | `content/` folder | medium | content authoring |

Phases 0–2 are independent and could land in a day. Phase 3 is the one that changes how the
package reads.

## What this audit did not check

- What Vercel actually bundles for the `api` service.
- Test counts, which are grep-based estimates.
- Whether any person or machine outside this repo runs `utilities/` or the terminal game.
