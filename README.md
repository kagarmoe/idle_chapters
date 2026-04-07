# Idle Chapters

A cozy text-based adventure game.

## Play the game

```bash
pip install -r requirements.txt
python -m idle_chapters
```

## Developer Setup

### Prerequisites

- Python 3.12+

### Install and run tests

```bash
pip install -r requirements.txt
pytest
```

### Local development

```bash
uvicorn idle_chapters.api.server:server
```

MongoDB is required for session persistence. Set `MONGO_URL` or run `mongod` locally.

- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Architecture

- **Game**: `idle_chapters/` — Python package (domain engine, content system, CLI).
- **Web API**: `idle_chapters/api/` — FastAPI REST layer
- **Database**: MongoDB
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
