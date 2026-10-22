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

### 2. Logs reach Axiom (already in place)

Found on 2026-10-22: Axiom's Vercel integration (installed 2026-09-30) already drains every
project on the team into the Axiom dataset `vercel` (org `kgarmoe-projects-hpnp`, edge
`us-east-1`): about 11k events a day, seconds behind. So there is no drain or ingest token
of our own; every query filters to this project.

- Every query starts from
  `['vercel'] | where ['vercel.projectName'] == 'idle-chapters' and ['vercel.environment'] == 'production'`.
- Vercel's own fields: `level`, `message`, `request.statusCode`, `request.path`,
  `report.durationMs`, `vercel.source` (`static`, `lambda`, `lambda-log`, …).
- The app's error line arrives as text in `message` (Vercel tags it `level: info`), so it is
  read with `extend e = parse_json(message) | where tostring(e.event) == 'error'`.
  Verified with a production 404: the line arrived with `kind: session_not_found` and the
  route template, not the raw id. Vercel's own request log line does carry the raw path.
- **Vault** `default` (this worktree): `axiom_token` (query, datasets, monitors, notifiers).
  `@john/axiom` reads it only from `AXIOM_TOKEN`, so a command that needs it reads it with
  `swamp vault read-secret` into that variable for one run.
- The Axiom behaviors live in `models/@john/`, which is gitignored (the owner's choice), so
  they are local to the checkout that has the vault.

### 3. Alerts (swamp, `@john/axiom-monitor` + `@john/axiom-notifier`)

- Notifier `axiom-discord`: type `discordWebhook`, the URL from
  `${{ vault.get("default", "discord_webhook_url") }}` (the owner chose Discord over email).
- Swamp's own posts to the same channel go through `@keeb/discord/webhook` (behavior
  `ic-alerts`, same vault key), for example a triage summary:
  `swamp behavior run ic-alerts send --input content=...`. A test post returned 204.
- Monitors, all Threshold type, each query dry-run against the last 24 h first:

  | Monitor | Query (after the base filter) | Fires when | Last 24 h |
  |---|---|---|---|
  | Server errors | app line `level == error`, or `request.statusCode >= 500` | > 0 in 5 min | 0 |
  | Browser errors | app line `source == browser` and `level == error` | > 5 in 15 min | 0 |
  | Handled errors | app line `level == warning` | > 20 in 15 min | 1 (a probe) |
  | Latency | p95 `report.durationMs` on `lambda` | > 2000 ms over 15 min | 281 ms (159 requests) |
  | Heartbeat | `request.path == '/health'` count | < 1 in 120 min, also on no data | 23 |

- The heartbeat window was 35 min and false-alarmed on the first night: GitHub had not yet
  started the new `*/15` cron, and its scheduled runs routinely start late or are skipped.
  At 120 min it fires only when the uptime job has really stopped.
- The handled-error monitor is a plain threshold, not anomaly detection: there is no
  history yet to learn a baseline from. Revisit once a few weeks of data exist.

### 4. Uptime

Axiom only sees traffic that happens. A scheduled GitHub Actions job requests `/health`
every 15 minutes; a failure fails the run, and GitHub emails the owner. It also keeps a
steady heartbeat in the logs, so an Axiom monitor with `alertOnNoData` on `/health` catches
an outage the job itself misses.

### 5. Reading it from swamp

- `swamp workflow run @john/axiom-error-triage --input dataset=vercel
  --input "errorPredicate=['vercel.projectName'] == 'idle-chapters' and tostring(parse_json(message).event) == 'error'"`
  counts errors by group and lists the latest ones.

## Order of work

1. App instrumentation (section 1). Done: PR #94.
2. The owner: Axiom account, org and token, plus the Discord webhook, in the vault. Done.
3. Logs into Axiom (section 2). Already in place through the Vercel integration.
4. Monitors and the Discord notifier (section 3). Queries are verified; this waits on the
   token gaining monitors and notifiers access.
5. Uptime job (section 4). Done: PR #95.
6. End to end: provoke a browser error, a handled 404 and a 500 in production; see each in
   Axiom; see the server-error alert in Discord.

## Not doing

- Tracing (`init_otel`) — errors and request logs answer the question; traces can come later.
- An error-tracking SDK (Sentry etc.) — the owner chose one pipeline through Axiom.
- Session replay, RUM performance metrics, a status page.
