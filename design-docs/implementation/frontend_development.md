# Frontend Development

## Overview

The browser-based game client lives in `apps/web/`. It is a SvelteKit application that communicates with the FastAPI backend over REST.

**Status:** Deployed at [idle-chapters.vercel.app/play/idle-chapters](https://idle-chapters.vercel.app/play/idle-chapters). One Vercel project serves the web app and the API on the same origin (Vercel Services; see `vercel.json` and the README's Deployment section).

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

The client always calls the API on its own origin. In dev, Vite forwards `/v1` and `/health` to the API on port 8000 (`vite.config.ts`); in production, Vercel routes them to the API service. The API's CORS settings only matter for other local origins.

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
| `JournalCard.svelte` | The journal so far, newest page first, folded until opened |
| `InventoryPanel.svelte` | What the player carries, who is nearby, and items here |

The play page also has a free-text box. *What can I do?*, *What is here?* and *Help* are
answered on the page and change nothing; anything else goes to `POST /v1/sessions/{id}/intent`,
and a no-match reply shows as a gentle note rather than the error screen.

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

- Error messages currently hardcoded in the Svelte component rather than using the `title` from the player projection's `ProblemDetail`
- No offline or service worker support
- No accessibility audit
