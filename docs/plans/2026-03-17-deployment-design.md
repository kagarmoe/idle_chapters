# Deployment Design: kimberlygarmoe.com + Idle Chapters

**Date:** 2026-03-17
**Status:** Approved

## Overview

Deploy Idle Chapters as a browser-playable game within a personal website at
kimberlygarmoe.com. The site uses SvelteKit on Vercel. The game backend runs
FastAPI on Railway, with MongoDB Atlas for persistence.

## Architecture

```
kimberlygarmoe.com (Vercel)          Railway              Atlas
+--------------------------+    +----------------+    +------------+
|  SvelteKit app           |    |  FastAPI        |    |  MongoDB   |
|                          |--->|  idle-chapters  |--->|  free tier |
|  /            landing    |    |  -api           |    +------------+
|  /projects    portfolio  |    +----------------+
|  /writing     writing    |
|  /data        dashboards |
|  /play        game lobby |
|  /play/idle-chapters     |
|  /thinking    essays     |
+--------------------------+
```

## Site Structure

| Route | Purpose | v1 Scope |
|-------|---------|----------|
| `/` | Landing page: name, tagline, nav | Build |
| `/projects` | Project portfolio | Stub |
| `/writing` | Writing portfolio | Stub |
| `/data` | Dashboards, visualizations | Stub |
| `/play` | Game lobby, list of playable demos | Build |
| `/play/idle-chapters` | Terminal UI for Idle Chapters | Build |
| `/thinking` | Essays, ideas, reflections | Stub |

## Frontend: SvelteKit on Vercel

Single SvelteKit app. Vercel deploys on push to main.

### Terminal Component (`<Terminal>`)

Hybrid aesthetic: terminal-inspired with modern UI touches.

**Visual style:**
- Dark background (#1a1a2e or similar), not pure black
- Monospace font for journal body, clean sans-serif for UI chrome
- Journal entries as styled cards with frontmatter headers (mood, place, time)
- Emoji or small icons for entry types (tea, garden, spell)
- Subtle glow or highlight on active journal entry
- Older entries dim and collapse

**Layout:**
- Scrollable journal history, newest at bottom
- Choice bar fixed at bottom: authored choices as styled buttons + free-text input
- Inventory panel: collapsible sidebar or modal

**Typewriter effect:**
- New journal text types in character-by-character (client-side)
- Choices appear after text finishes
- Click-to-skip for impatient players

### Splash Screen

On load, `/play/idle-chapters` shows an ASCII art splash:
- Elaborate ASCII art of "Idle Chapters" with decorative objects woven into,
  around, and below the letters: teacups, pillows, animals, gems, mirror
- Types in or fades in on first load
- Menu below: "New Game" and "Continue" (Continue only if session in localStorage)
- Tagline: "a cozy text adventure"
- Selecting a menu option transitions to the journal/choice UI

### State Management

- Session ID in localStorage (persist across reloads)
- On load: check for existing session, resume or show splash
- All game state on the server; frontend is a thin display layer

### Communication

- REST only, calling existing `/v1/sessions/*` and `/v1/world/*` endpoints
- No WebSockets needed; turn-based game fits request/response
- Typewriter effect is purely client-side after receiving full response

## Backend: FastAPI on Railway

The existing API is deployment-ready. Changes needed:

1. **CORS middleware** - Allow Vercel origin (kimberlygarmoe.com)
2. **Health check** - `GET /health` endpoint
3. **Environment config** - MongoDB Atlas connection string via env var

No new game endpoints. Railway deploys on push to main, watches the api
directory. Free tier sleeps after 10 min inactivity; $5/month Hobby plan
if cold starts become a problem.

## MongoDB: Atlas Free Tier

- Managed cloud MongoDB, 512MB free
- Single cluster, `idle_chapters` database
- Connection string as Railway environment variable
- More than enough for text game state

## Repository Structure

Two repos connected via git submodules:

```
kagarmoe/kimberlygarmoe.com    (personal site — owns deployment)
+-- apps/
|   +-- idle-chapters/         <- git submodule -> kagarmoe/idle_chapters
|       +-- apps/api/          <- FastAPI (Railway deploys from here)
|       +-- apps/web/          <- SvelteKit (Vercel deploys from here)
+-- .github/
|   +-- workflows/             <- CI triggers on submodule changes
```

```
kagarmoe/idle_chapters         (game repo — owns game code)
+-- apps/
|   +-- api/                   <- FastAPI backend + game content
|   +-- web/                   <- SvelteKit frontend + terminal UI
+-- .github/
|   +-- workflows/
|       +-- web.yml            <- lint, type-check, build
|       +-- api.yml            <- lint, pytest
```

**Why submodules:** idle_chapters keeps its own repo, history, and CI.
The personal site repo references it and handles deployment config.
Future games/projects get their own repos and submodule entries.

Vercel and Railway both support git submodules natively.

## CI/CD: GitHub Actions

**In idle_chapters repo:**
- web.yml: lint -> type-check -> build (on push to apps/web/**)
- api.yml: lint -> pytest (on push to apps/api/**)

**In kimberlygarmoe.com repo:**
- Vercel auto-deploys on push (reads submodule for apps/web/)
- Railway auto-deploys on push (reads submodule for apps/api/)

## Backend Changes (Already Done)

1. CORSMiddleware added to `app/api/app.py`
2. `GET /health` endpoint added
3. `MONGO_URL` env var drives connection
4. Dockerfile included for Railway

## Decisions

- **REST only** - No WebSockets. Turn-based game fits request/response.
- **Git submodules** - Game repos stay independent. Site repo references them for deployment.
- **Railway for backend** - Deploys from GitHub, handles Python natively, $0-5/month.
- **Atlas for MongoDB** - Managed, free tier, zero ops.
- **localStorage for session** - Simple, no auth needed for v1.
- **Stubs for non-game sections** - Ship the site structure early, fill in content later.
