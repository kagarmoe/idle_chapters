# Feature priorities — 2026-10-21

Source: a full read of `design-docs/` compared against the code (58 features, F01–F58; the inventory lives with this
doc as `2026-10-21-feature-inventory.md`). Ordering rules, in order:

1. **Playable before bigger.** Anything that stops a player from starting, continuing or moving through the world comes
   first.
2. **Deterministic.** Same session + same state → same scene and same journal page. No re-roll on reconnect.
3. **Tone contract wins.** A feature that adds urgency, scarcity, failure, judgment or obligation goes to *Not doing*,
   however it is phrased in a draft.
4. **Smallest slice that is complete.** Each item ships with a test that runs in CI, through the `ic` factory.

## P0 — playable and honest (do first)

| # | Feature | IDs | Size | Why now |
|---|---|---|---|---|
| 1 | Splash menu never appears (New Game unreachable on the web) | F44 | S | Blocks all web play |
| 2 | Continue shows an empty scene | F30, F44 | S | `GET /sessions/{id}` returns an empty view; resume must re-render the current node |
| 3 | Travel: leave the cottage, reach town and the other zones | F21, F06 | M | Done for zone roots (ic-5). Follow-ups: sub-places, cottage homecoming scene |
| 4 | Pin the API's projection default (re-scoped) | F39 | S | Developer stays the default, by the author's choice (commit 1bc483c: the API serves developers, the frontend serves players). Existing tests cover both headers on the real app; nothing pinned the omitted-header default, so a test now does. The web client's player header is still untested |
| 5 | Deterministic scenes: seed from session + state | F34, F20 | S | Reconnect re-rolls the scene; `result_variants` unpicked |
| 6 | Visit counts update (done, ic-4: arrivals, not refreshes) | F19 | S | Seen interactions moved to #8, since nothing performs interactions yet |
| 7 | Cross-file integrity checked at startup | F02 | S | Fail fast on broken content (the bug fixed in #59) |

## P1 — the world comes alive

| # | Feature | IDs | Size |
|---|---|---|---|
| 8 | NPC interactions surface in play (ambient, micro-offer, ritual, light request, threshold) + `visible_npcs`, counting `seen_interactions` | F08, F09, F19 | L |
| 9 | Free-text intent via `intent_signature` + "what can I do / what is here" | F25, F26 | M |
| 10 | Web client: free-text input, journal history, inventory panel data, no raw scene id, journal card title | F44 | M |
| 11 | Soft time of day (advances by action; no clock, no deadlines) | F18, F05 | M |
| 12 | Tea ritual from recipes (ingredients are bountiful: noted, never spent) | F14, F13 | M |
| 13 | Procedural scenes shaped like interactions, lexicon-safe | F22, F23, F24 | M |

## P2 — depth and housekeeping

| # | Feature | IDs | Size |
|---|---|---|---|
| 14 | CLI plays through `SessionService` (retire the hardcoded cottage and file saves in `assets/`) | F27, F29 | M |
| 15 | Players linked to sessions (journal/inventory endpoints return real data) | F33 | M |
| 16 | Session TTL / cleanup (needed before a free-tier Mongo) | F37 | S |
| 17 | Lexicon check for authored action text and journal prose | F24 | M |
| 18 | NPC address rules (optional vocatives, fixed pools) | F10 | M |
| 19 | Spells and thin-place portals (optional, never instructional) | F15 | L |
| 20 | Player notes left in places (observational, not confessional) | F50 | M |
| 21 | `/sessions/{id}/events` + domain events | F31, F43 | S |
| 22 | Keyboard-accessible typewriter skip; a11y pass | F58 | S |
| 23 | Richer journal prose from lexicons; collision-free page ids | F12 | M |
| 24 | Stale docs reconciled (ARCHITECTURE, errors default, frontend status, API_GENERATION superseded) | — | S |

## Not doing

| Feature | IDs | Reason |
|---|---|---|
| Energy / mood stats restored by naps and snacks | F17 | Resource management; "rest is not remediation" (players_design), tone §3 |
| "No bed-rotting" — day advances only when you leave | F17, F18 | Judges rest; contradicts "you are allowed to be where you are" |
| Shop and money | F51 (shop) | Economy and scarcity; ARCHITECTURE non-goal |
| Spending ingredients / "insufficient inventory" | F13, F14 | Scarcity framing; ingredients stay bountiful |
| Places "spent" until revisited before spell reuse | F15 | Obligation and scarcity (tone §3) |
| `restless` and other out-of-range moods | — | Outside the allowed emotional range (tone §7) |
| Relationship / affinity scores | F52 | Drifts into reward escalation and obligation (interactions_design §3.3) |
| Separate Notebook | F16 | Duplicates the journal; the journal is the notebook |
| Runtime LLM scene generation | F47 | Breaks determinism and needs a tone gate per output; authored + procedural content first |
| Typer CLI with fuzzy matching | F28 | Superseded by F25 intent parsing + F27 CLI-over-service |
| Spec-first OpenAPI codegen | F41 | Superseded by code-first export (done) |
| Content CRUD SDK, live content editing in Mongo | F49, F38 | No user for it; content is versioned JSON |
| Content-version pinning per session | F36 | Not needed until content changes under live sessions matter |

## Deployment

- Web: Vercel project `idle-chapters` (Git-connected, `main` → production).
- API: Vercel project `idle-chapters-api` (FastAPI preset) at https://idle-chapters-api.vercel.app, with
  `MONGO_URL=memory://` as a stopgap (sessions are per server instance and reset on cold start).
- **Needs the author:** a MongoDB connection string (Atlas free tier per the 2026-03-17 deployment design) stored in the
  swamp vault as `api_mongo_url`, and connecting the API project to GitHub in the Vercel dashboard (or a
  Vercel token with project-write scope in the vault).
- Deviation from the 2026-03-17 design: the API is on Vercel, not Railway (no Railway account or token available; same
  FastAPI app, so moving later is a config change).
