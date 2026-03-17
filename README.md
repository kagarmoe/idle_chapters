# Idle Chapters

A cozy text-based adventure game. Play in your browser at [kimberlygarmoe.com/play/idle-chapters](https://kimberlygarmoe.com/play/idle-chapters).

## Architecture

Monorepo with two apps:

```
apps/
├── api/    ← FastAPI backend (Python)
└── web/    ← SvelteKit frontend (TypeScript)
```

- **Frontend**: SvelteKit + Tailwind CSS, deployed to Vercel
- **Backend**: FastAPI + PyMongo, deployed to Railway
- **Database**: MongoDB Atlas (free tier)
- **CI**: GitHub Actions (`.github/workflows/`)

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 22+
- MongoDB (local or Atlas connection string)

### 1. Start MongoDB

Local:
```bash
mongod --dbpath ./data/mongo
```

Or set a remote connection string:
```bash
export MONGO_URL="mongodb+srv://user:pass@cluster.mongodb.net/"
export MONGO_DB="idle_chapters"
```

### 2. Run the API

```bash
cd apps/api
pip install -r requirements.txt
python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Run the frontend

```bash
cd apps/web
npm install
npm run dev
```

Site: [http://localhost:5173](http://localhost:5173)
Game: [http://localhost:5173/play/idle-chapters](http://localhost:5173/play/idle-chapters)

The frontend reads `VITE_API_URL` (defaults to `http://localhost:8000`).

### 4. Run the CLI (optional)

```bash
cd apps/api
python -m app.main
```

## Testing

```bash
# API tests (excludes MongoDB-dependent tests)
cd apps/api
python -m pytest tests/ -v --ignore=tests/test_persistence.py

# API tests including MongoDB (requires MONGO_URL)
MONGO_URL="mongodb://localhost:27017" python -m pytest tests/ -v

# Frontend type-check and build
cd apps/web
npm run check
npm run build
```

## Deployment

### Frontend (Vercel)

1. Connect the repo to Vercel
2. Set root directory to `apps/web`
3. Set environment variable: `VITE_API_URL=https://<your-railway-domain>`
4. Add custom domain: `kimberlygarmoe.com`

### Backend (Railway)

1. Create a Railway project from the repo
2. Set root directory to `apps/api`
3. Start command: `python -m uvicorn app.api.app:app --host 0.0.0.0 --port $PORT`
4. Set environment variables:
   - `MONGO_URL` — Atlas connection string
   - `MONGO_DB` — `idle_chapters`
   - `CORS_ORIGINS` — `https://kimberlygarmoe.com,http://localhost:5173`

### Database (MongoDB Atlas)

1. Create a free M0 cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a database user
3. Allow network access (Railway IPs or `0.0.0.0/0` for free tier)
4. Copy the connection string to Railway's `MONGO_URL` env var

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
apps/api/
├── app/
│   ├── api/          ← FastAPI app, routers, models
│   ├── content/      ← Content loading, schemas, validation
│   ├── domain/       ← Engine, state, effects, selectors
│   ├── persistence/  ← MongoDB stores (state, journal, events)
│   └── services/     ← SessionService orchestrator
├── assets/           ← Game content (JSON)
├── schemas/          ← JSON schemas
├── lexicons/         ← Word lists for procedural generation
└── tests/

apps/web/
├── src/
│   ├── lib/          ← Components (Splash, JournalCard, etc.) + API client
│   └── routes/       ← SvelteKit pages (/, /play, /projects, etc.)
└── static/
```
