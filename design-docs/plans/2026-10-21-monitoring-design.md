# Monitoring idle-chapters.vercel.app — design

Epic: `chapters-0zq`. Decided with the owner (2026-10-21): **Axiom** is the backend; the
Vercel team is on **Pro**, so log drains are available.

## Goal

See what the live site is doing: traffic, latency, status codes, and **every error,
including non-fatal ones** (handled API errors, a player-facing "the path fades" message,
an unhandled promise in the browser). Get told when something is wrong without having to
look.

## Today

- Nothing is captured. `idle_chapters/telemetry.py:init_otel` exists but nothing calls it,
  and it only does tracing.
- The API's `GameError` handler (`api/server.py`) turns errors into RFC 9457 responses and
  logs nothing. Unhandled exceptions reach Vercel's runtime logs only as stderr tracebacks.
- The web client's `handleError` (`routes/play/idle-chapters/+page.svelte`) shows the
  player a gentle message and drops the error. Browser errors never reach any server.
- One Vercel project serves both (`vercel.json` services: `api` FastAPI, `web` SvelteKit).

## Design

```
browser ──(errors, beacon)──▶ POST /v1/client-errors ─┐
SvelteKit SSR (hooks.server handleError) ─────────────┤  one JSON line per event
FastAPI (GameError + unhandled handlers) ─────────────┤  on stdout/stderr
Vercel edge/static/lambda request logs ───────────────┘
            │  Vercel log drain (@swamp/vercel/drains, production only)
            ▼
        Axiom dataset `idle-chapters`
            │  monitors + email notifier (@john/axiom)
            ▼
     alerts; swamp reads back with @john/axiom-error-triage
```

### 1. The app reports its errors (code, vendor-neutral)

Every error becomes one structured JSON log line, so it lands in Vercel's runtime logs and,
through the drain, in Axiom. Shape:

```json
{"event": "error", "level": "warning|error", "source": "api|ssr|browser",
 "kind": "...", "status": 404, "method": "POST", "path": "/v1/sessions/{id}/choose",
 "message": "...", "stack": "...", "commit": "<VERCEL_GIT_COMMIT_SHA>"}
```

- **API.** The `GameError` handler logs `warning` for 4xx (handled, non-fatal) and `error`
  for 5xx. A new catch-all `Exception` handler logs `error` with the traceback and returns a
  plain RFC 9457 500. The path is the route template, never the raw URL, so session ids and
  query strings stay out of the logs.
- **Browser.** `hooks.client.ts` `handleError` (SvelteKit's unexpected errors), `window`
  `error` and `unhandledrejection`, and the play page's own `handleError` (handled
  `ApiError`s, the non-fatal case) send `navigator.sendBeacon('/v1/client-errors', …)`.
  At most 10 per page load, each distinct message once.
- **`POST /v1/client-errors`** (new API route, unauthenticated, so it is a trust
  boundary): a Pydantic body with every string length-capped (kind 100, message 500, path
  200, stack 4000) and unknown fields refused, logged as `source: browser`, `204` back.
  Nothing the player typed is sent: message, stack, path without query, user agent.
  It is unauthenticated, so it can be spammed; the caps bound each line, and a Vercel
  Firewall rate limit on the path is the follow-up if volume ever shows it.
- **SSR.** `hooks.server.ts` `handleError` logs the same line for server-rendering errors.
- `docs/openapi.json` is regenerated for the new route (CI checks it).

### 2. Logs reach Axiom (swamp)

- **Vault** `default`: `axiom_token` (an Axiom API token that can manage datasets, monitors
  and notifiers and run queries; swamp's own use) and `axiom_ingest_token` (ingest-only,
  scoped to the one dataset; it goes in the drain's header).
- **Behaviors**, each committed under `models/`:
  - `@john/axiom-dataset` → dataset `idle-chapters`.
  - `@swamp/vercel/drains/drains` → drain `idle-chapters-axiom`: project
    `idle-chapters` only, production only, sources `lambda`, `edge`, `static`, `external`,
    `firewall`, `build`; HTTP NDJSON to
    `https://api.axiom.co/v1/datasets/idle-chapters/ingest`,
    `Authorization: Bearer ${{ vault.get("default", "axiom_ingest_token") }}`.
- Risk: the drain's `headers` field is not marked sensitive (its `secret` field is), so the
  ingest token may appear in the drain's stored data. Hence an ingest-only, single-dataset
  token: the worst a leak allows is writing junk into this dataset.

### 3. Alerts (swamp, `@john/axiom-monitor` + `@john/axiom-notifier`)

- Notifier: email to the owner.
- Monitors (5-minute interval unless noted):
  - **Server errors**: any `level == "error"` from `api`/`ssr`, or any 5xx request. Threshold > 0.
  - **Browser errors**: `source == "browser"` and `level == "error"`, more than 5 in 15 minutes.
  - **Handled-error spike**: `level == "warning"` above a baseline (anomaly detection), so a
    rise in 4xx shows even though none is fatal.
  - **Latency**: p95 request duration over 2 s for 15 minutes.
- Exact field names for Vercel's request logs in Axiom are confirmed from the first ingested
  events before the monitor APL is written; the app's own lines use the shape above.

### 4. Uptime

Axiom only sees traffic that happens. A scheduled GitHub Actions job requests `/health`
every 15 minutes; a failure fails the run, and GitHub emails the owner. It also keeps a
steady heartbeat in the logs, so an Axiom monitor with `alertOnNoData` on `/health` catches
an outage the job itself misses.

### 5. Reading it from swamp

- `swamp workflow run @john/axiom-error-triage --input dataset=idle-chapters
  --input "errorPredicate=tostring(['level']) in ('warning', 'error')"` — counts by source
  and kind, plus the latest events.
- A setup workflow, `ic-monitoring`, creates or updates the dataset, drain, notifier and
  monitors, so the whole stack is re-creatable from the repo.

## Order of work

1. App instrumentation (section 1) — a PR with tests; no account needed.
2. **The owner:** an Axiom account and org, the two tokens, stored with
   `swamp vault put default axiom_token` and `… axiom_ingest_token`; confirm the alert email.
3. Dataset and drain (section 2). The drain is an outward-facing change on the production
   project: confirm before creating it.
4. Monitors and notifier (section 3), after the first events show the real field names.
5. Uptime job (section 4).
6. End to end: provoke a browser error, a handled 404 and a 500 in production; see each in
   Axiom; see the server-error monitor email.

## Not doing

- Tracing (`init_otel`) — errors and request logs answer the question; traces can come later.
- An error-tracking SDK (Sentry etc.) — the owner chose one pipeline through Axiom.
- Session replay, RUM performance metrics, a status page.
