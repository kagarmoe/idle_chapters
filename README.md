# idle_chapters

Idle Chapters is a cozy text-based game about nothing much at all.

## Dependencies

FastAPI server + Mongo driver:

- `fastapi`
- `uvicorn`
- `pymongo`

Install:

```
python -m pip install -r requirements.txt
```

## Run MongoDB

If you use a local MongoDB instance:

```
mongod --dbpath ./data/mongo
```

Set env vars if needed:

```
export MONGO_URL="mongodb://localhost:27017"
export MONGO_DB="idle_chapters"
```

## Run the API

```
python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

## API URLs

Docs + OpenAPI:

http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json

Example:

http://127.0.0.1:8000/v1/world/manifest
