# Package Rename Design: app → idle_chapters

## Status

**Approved design** — ready for implementation planning.

## Problem

The Python package is named `app`, producing imports like `from app.api.app import app` — four levels of the same meaningless word. The `apps/api/` monorepo nesting adds unnecessary depth and requires `PYTHONPATH` manipulation to run anything. The Zen of Python says: flat is better than nested, readability counts, namespaces are one honking great idea.

## Design

Move `apps/api/app/` to `idle_chapters/` at the repository root. Mirror the package structure in the test directory.

### Package Structure

```
idle_chapters/
    __init__.py
    __main__.py              # python -m idle_chapters
    main.py                  # CLI entrypoint
    telemetry.py
    api/
        server.py            # was app.py; FastAPI instance renamed to server
        deps.py
        models.py
        routers/
            __init__.py
            sessions.py
            players.py
            world.py
            journal.py
    domain/
        engine.py
        state.py
        conditions.py
        effects.py
        selector.py
        scene.py
        scene_generator.py
        step_result.py
        ingredient_picker.py
        journal_renderer.py
    content/
        loader.py
        repo.py
        manifest.py
        validators.py
        schema_utils.py
    persistence/
        mongo.py
        state_store.py
        journal_store.py
        event_store.py
    services/
        session_service.py
    scenes/
        __init__.py
        cottage.py
        inventory.py
        welcome.py
    ui/
        __init__.py
        text.py
```

### Test Structure (Mirrored)

```
tests/
    conftest.py
    api/
        test_api.py
    domain/
        test_engine.py
        test_effects.py
        test_conditions.py
        test_scene_generation.py
    content/
        test_content_loader.py
        test_content_manifest.py
        test_content_repo.py
        test_validators.py
    journal/
        test_journal_renderer.py
    persistence/
        test_persistence.py
    player/
        test_player.py
        test_player_schema.py
    assets/
        test_backfill_assets.py
        test_update_assets.py
        test_repo_structure.py
```

### Files Moved or Deleted

| From | To |
|---|---|
| `apps/api/app/` | `idle_chapters/` |
| `apps/api/app/api/app.py` | `idle_chapters/api/server.py` |
| `apps/api/tests/` | `tests/` (mirrored subdirectories) |
| `apps/api/pyproject.toml` | `pyproject.toml` (repo root) |
| `apps/api/requirements.txt` | `requirements.txt` (repo root) |
| `apps/api/Dockerfile` | `Dockerfile` (repo root) |
| `apps/api/PYTHONPATH` | Deleted (no longer needed) |
| `app/` | Deleted (ghost directory, stale __pycache__ only) |
| `tests/` (old, at root) | Replaced by mirrored structure |

### Import Changes

Every `from app.` becomes `from idle_chapters.`:

```python
# Before
from app.api.app import app
from app.domain.engine import Engine
from app.services.session_service import SessionService

# After
from idle_chapters.api.server import server
from idle_chapters.domain.engine import Engine
from idle_chapters.services.session_service import SessionService
```

### Entry Points

| Action | Command |
|---|---|
| Run CLI | `python -m idle_chapters` |
| Run API server | `uvicorn idle_chapters.api.server:server` |
| Run tests | `pytest` |

No `PYTHONPATH` manipulation needed. Python finds `idle_chapters/` at the repo root naturally.

### Configuration Changes

**`pytest.ini`:**
```ini
[pytest]
testpaths = tests
addopts = -ra
env =
    OTEL_SDK_DISABLED=true
```

**`Dockerfile`:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY idle_chapters ./idle_chapters
COPY assets ./assets
COPY schemas ./schemas
COPY lexicons ./lexicons
EXPOSE 8000
CMD ["uvicorn", "idle_chapters.api.server:server", "--host", "0.0.0.0", "--port", "8000"]
```

### Downstream Updates

- `design-docs/plans/2026-04-04-structured-errors-plan.md` — all `from app.` imports must be updated to `from idle_chapters.`
- `.github/workflows/api.yml` — update paths if they reference `apps/api/`

## Acceptance Criteria

- No `app/` or `apps/api/app/` directory exists
- No `from app.` or `import app.` in any Python file
- No `PYTHONPATH` manipulation anywhere
- `python -m idle_chapters` starts the CLI
- `uvicorn idle_chapters.api.server:server` starts the API
- `pytest` passes (93+ tests)
- Dockerfile builds
