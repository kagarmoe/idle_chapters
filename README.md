# Idle Chapters

A cozy text-based adventure game.

## Play the game

```bash
pip install -r requirements.txt
python -m idle_chapters
```

Or play in your browser at [kimberlygarmoe.com/play/idle-chapters](https://kimberlygarmoe.com/play/idle-chapters).

## Developer Setup

### Prerequisites

- Python 3.12+
- Node.js 22+ (for the web frontend)

### Install and run tests

```bash
pip install -r requirements.txt
pytest
```

### Web deployment (API + frontend)

The browser version runs as two services deployed separately. For local web development:

```bash
# Terminal 1: API server (serves game state over REST)
uvicorn idle_chapters.api.server:server

# Terminal 2: SvelteKit frontend
cd apps/web && npm install && npm run dev
```

MongoDB is required for session persistence. Set `MONGO_URL` or run `mongod` locally.

- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Game: [http://localhost:5173/play/idle-chapters](http://localhost:5173/play/idle-chapters)

## Architecture

- **Game**: `idle_chapters/` — Python package (domain engine, content system, CLI)
- **Web API**: `idle_chapters/api/` — FastAPI REST layer, deployed to Railway
- **Web frontend**: `apps/web/` — SvelteKit + Tailwind CSS, deployed to Vercel
- **Database**: MongoDB Atlas (free tier, web version only)
- **CI**: GitHub Actions (`.github/workflows/`)
- **API docs**: [kagarmoe.github.io/idle_chapters](https://kagarmoe.github.io/idle_chapters/) (GitHub Pages)

## Documentation

- **`design-docs/`** — Game design, implementation specs, and plans
- **`docs/`** — [GitHub Pages site](https://kagarmoe.github.io/idle_chapters/) (auto-generated OpenAPI spec)

## Testing

```bash
# API tests (excludes MongoDB-dependent tests)
pytest --ignore=tests/persistence/

# API tests including MongoDB (requires MONGO_URL)
MONGO_URL="mongodb://localhost:27017" pytest

# Frontend type-check and build
cd apps/web
npm run check
npm run build
```

## Deployment

This repo is deployed via [kagarmoe/kimberlygarmoe.com](https://github.com/kagarmoe/kimberlygarmoe.com),
which references it as a git submodule.

### Site repo setup (kimberlygarmoe.com)

```bash
# In the kimberlygarmoe.com repo:
git submodule add https://github.com/kagarmoe/idle_chapters.git apps/idle-chapters
git submodule update --init --recursive
```

### Frontend (Vercel)

1. Connect `kagarmoe/kimberlygarmoe.com` to Vercel
2. Set root directory to `apps/idle-chapters/apps/web`
3. Set environment variable: `VITE_API_URL=https://<your-railway-domain>`
4. Add custom domain: `kimberlygarmoe.com`
5. Enable git submodules in Vercel project settings

### Backend (Railway)

1. Create a Railway project from `kagarmoe/kimberlygarmoe.com`
2. Set root directory to `apps/idle-chapters`
3. Start command: `uvicorn idle_chapters.api.server:server --host 0.0.0.0 --port $PORT`
4. Set environment variables:
   - `MONGO_URL` — Atlas connection string
   - `MONGO_DB` — `idle_chapters`
   - `CORS_ORIGINS` — `https://kimberlygarmoe.com,http://localhost:5173`

### Database (MongoDB Atlas)

1. Create a free M0 cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a database user
3. Allow network access (Railway IPs or `0.0.0.0/0` for free tier)
4. Copy the connection string to Railway's `MONGO_URL` env var

### Updating the submodule

When idle_chapters is updated, bump the submodule ref in the site repo:

```bash
cd apps/idle-chapters
git pull origin main
cd ../..
git add apps/idle-chapters
git commit -m "chore: update idle-chapters submodule"
git push
```

Vercel and Railway will redeploy automatically.

### Verify

```bash
# Health check
curl https://<railway-domain>/health
# Expected: {"status":"ok"}

# Create a session
curl -X POST https://<railway-domain>/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"place_id": "cottage_home"}'
```

## Project Structure

```
idle_chapters/       ← Python package
├── api/             ← FastAPI server, routers, models
├── content/         ← Content loading, schemas, validation
├── domain/          ← Engine, state, effects, selectors
├── persistence/     ← MongoDB stores (state, journal, events)
├── services/        ← SessionService orchestrator
├── scenes/          ← CLI scene logic
└── ui/              ← CLI text output

tests/               ← Mirrored test structure
├── api/
├── domain/
├── content/
├── journal/
├── persistence/
├── player/
└── assets/

assets/              ← Game content (JSON)
schemas/             ← JSON schemas
lexicons/            ← Word lists for procedural generation

apps/web/            ← SvelteKit frontend
├── src/
│   ├── lib/         ← Components + API client
│   └── routes/      ← SvelteKit pages
└── static/

design-docs/
├── game_design/     ← Tone, storylets, interactions, player design
├── implementation/  ← Architecture, API design, engine specs
└── plans/           ← Design docs and implementation plans

docs/                ← GitHub Pages (OpenAPI spec + ReDoc viewer)
```
