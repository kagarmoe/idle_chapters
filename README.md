# idle_chapters

Idle Chapters is a cozy text-based game about nothing much at all.

## Documentation

The Idle Chapters [documentation](https://kagarmoe.github.io/idle_chapters/) is published on GitHub Pages.

## Quickstart

1. Clone repo

1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

1. Start services

```bash
mongod --dbpath ./data/mongo
```

Optional env vars:

```bash
export MONGO_URL="mongodb://localhost:27017"
export MONGO_DB="idle_chapters"
```

1. Run app

Run the API:

```bash
python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Run the game (CLI):

```python
python -m app.main
```

1. Look at the API documentation

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
[http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)
