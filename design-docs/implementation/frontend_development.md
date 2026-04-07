# Frontend Development

## Overview

The browser-based game client lives in `apps/web/`. It is a SvelteKit application that communicates with the FastAPI backend over REST.

**Status:** Functional prototype. Not deployed. Local development only.

## Tech Stack

- **SvelteKit** (Svelte 5, runes mode)
- **Tailwind CSS 4**
- **TypeScript**
- **Vite 7**

## Prerequisites

- Node.js 22+
- The API server running locally (`uvicorn idle_chapters.api.server:server`)
- MongoDB running for session persistence

## Running Locally

```bash
cd apps/web
npm install
npm run dev
```

The game is available at [http://localhost:5173/play/idle-chapters](http://localhost:5173/play/idle-chapters).

The API base URL is configured via the `VITE_API_URL` environment variable. When unset, it defaults to the same origin (expects the API at the same host).

## Architecture

### Pages

| Route | Purpose |
|---|---|
| `/play/idle-chapters` | The game client |
| `/play` | Play index |
| `/data` | Data browser |
| `/projects` | Projects listing |
| `/writing` | Writing portfolio |
| `/thinking` | Thinking portfolio |

### Components

| Component | Purpose |
|---|---|
| `Splash.svelte` | Title screen with new game / continue options |
| `Typewriter.svelte` | Animated text reveal for scene prompts |
| `ChoiceBar.svelte` | Action buttons (disabled until typewriter finishes) |
| `JournalCard.svelte` | Displays the current journal page |
| `InventoryPanel.svelte` | Shows visible items and NPCs |

### API Client

`src/lib/api.ts` — Typed client covering `/v1/sessions/*` and `/v1/world/*` endpoints. Types are derived from `docs/openapi.json` component schemas.

Key design decisions:

- **Sends `Accept-Projection: player` on all requests.** The frontend is the player-facing interface, so it always requests the player projection.
- **Parses RFC 9457 error responses.** `ApiError` extracts the `ProblemDetail` body so the game can show tone-contract-compliant error messages from the player projection's `title` field.
- **Session persistence uses `localStorage`.** The session ID is saved under `idle-chapters-session-id`. On return, the client attempts to resume; if the session is 404, it clears the save and returns to the splash screen.

### Game Loop

```
Splash → create/resume session → playing (prompt + choices) → action → playing → ...
                                                                ↓ (on error)
                                                              error screen → splash
```

The game screen is a state machine: `splash | loading | playing | error`. Errors show a tone-appropriate message and offer a return to the title screen.

## Quality Checks

```bash
cd apps/web
npm run check     # svelte-check + TypeScript
npm run build     # Production build
```

## What's Not Built Yet

- Deployment configuration (no hosting target chosen)
- Error messages currently hardcoded in the Svelte component rather than using the `title` from the player projection's `ProblemDetail`
- No offline or service worker support
- No accessibility audit
