# Package Rename Implementation Plan: app → idle_chapters

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the Python package from `app` to `idle_chapters`, flatten the directory structure, and mirror tests to match.

**Architecture:** Move `apps/api/app/` → `idle_chapters/` at repo root. Move `apps/api/tests/` → `tests/` with mirrored subdirectories. Update all imports, config, Dockerfile, and CI. No new logic — purely mechanical.

**Tech Stack:** Python 3.12+, FastAPI, pytest, git mv

**Design doc:** `design-docs/plans/2026-04-04-package-rename-design.md`

---

### Task 1: Move the package

**Files:**
- Move: `apps/api/app/` → `idle_chapters/`
- Rename: `idle_chapters/api/app.py` → `idle_chapters/api/server.py`
- Create: `idle_chapters/__main__.py`
- Delete: `app/` (ghost directory with stale __pycache__)

**Step 1: Delete the ghost directory**

```bash
rm -rf app/
```

**Step 2: Move the package using git mv**

```bash
git mv apps/api/app idle_chapters
```

**Step 3: Rename api/app.py to api/server.py**

```bash
git mv idle_chapters/api/app.py idle_chapters/api/server.py
```

**Step 4: Rename the FastAPI instance in server.py**

In `idle_chapters/api/server.py`, change the last line:

From:
```python
app = create_app()
```

To:
```python
server = create_app()
```

**Step 5: Create `__main__.py`**

```python
# idle_chapters/__main__.py
"""Entry point for python -m idle_chapters."""
from idle_chapters.main import main

main()
```

**Step 6: Commit**

```bash
git add idle_chapters/ app/
git commit -m "refactor: move apps/api/app to idle_chapters at repo root"
```

---

### Task 2: Update all imports in the package

**Files:**
- Modify: every `.py` file under `idle_chapters/`

**Step 1: Replace all imports**

In every `.py` file under `idle_chapters/`, replace:
- `from app.` → `from idle_chapters.`
- `import app.` → `import idle_chapters.`

Also in `idle_chapters/api/server.py`, update the router imports:

From:
```python
from app.api.routers import journal, players, sessions, world
```

To:
```python
from idle_chapters.api.routers import journal, players, sessions, world
```

The full list of files with imports to change (105 occurrences across these files):

```
idle_chapters/api/server.py
idle_chapters/api/deps.py
idle_chapters/api/routers/sessions.py
idle_chapters/api/routers/players.py
idle_chapters/api/routers/world.py
idle_chapters/api/routers/journal.py
idle_chapters/content/loader.py
idle_chapters/content/repo.py
idle_chapters/domain/engine.py
idle_chapters/domain/effects.py
idle_chapters/domain/conditions.py
idle_chapters/domain/selector.py
idle_chapters/domain/scene_generator.py
idle_chapters/domain/step_result.py
idle_chapters/persistence/state_store.py
idle_chapters/persistence/event_store.py
idle_chapters/persistence/journal_store.py
idle_chapters/services/session_service.py
idle_chapters/scenes/cottage.py
idle_chapters/scenes/inventory.py
idle_chapters/scenes/welcome.py
idle_chapters/main.py
```

**Step 2: Verify the package loads**

Run: `.venv/bin/python -c "from idle_chapters.api.server import server; print(server.title)"`
Expected: `Idle Chapters API`

Run: `.venv/bin/python -c "from idle_chapters.main import main; print('CLI loads')"`
Expected: `CLI loads`

**Step 3: Commit**

```bash
git add idle_chapters/
git commit -m "refactor: update all imports from app to idle_chapters"
```

---

### Task 3: Move and restructure tests

**Files:**
- Move: `apps/api/tests/` → `tests/` (mirrored subdirectories)
- Move: `apps/api/tests/fixtures/` → `tests/fixtures/`
- Keep: `tests/test_tone_prompt_coverage.py` (already exists at root)

**Step 1: Remove stale root tests directory contents and move**

The root `tests/` already exists with one file. Move the API tests into mirrored subdirectories:

```bash
# Create mirrored directories
mkdir -p tests/api tests/domain tests/content tests/journal tests/persistence tests/player tests/assets tests/fixtures

# Move test files to mirrored locations
git mv apps/api/tests/test_api.py tests/api/
git mv apps/api/tests/test_engine.py tests/domain/
git mv apps/api/tests/test_effects.py tests/domain/
git mv apps/api/tests/test_conditions.py tests/domain/
git mv apps/api/tests/test_scene_generation.py tests/domain/
git mv apps/api/tests/test_content_loader.py tests/content/
git mv apps/api/tests/test_content_manifest.py tests/content/
git mv apps/api/tests/test_content_repo.py tests/content/
git mv apps/api/tests/test_validators.py tests/content/
git mv apps/api/tests/test_journal_renderer.py tests/journal/
git mv apps/api/tests/test_persistence.py tests/persistence/
git mv apps/api/tests/test_player.py tests/player/
git mv apps/api/tests/test_player_schema.py tests/player/
git mv apps/api/tests/test_backfill_assets.py tests/assets/
git mv apps/api/tests/test_update_assets.py tests/assets/
git mv apps/api/tests/test_repo_structure.py tests/assets/

# Move fixtures
git mv apps/api/tests/fixtures/player.json tests/fixtures/
git mv apps/api/tests/fixtures/players.json tests/fixtures/
git mv apps/api/tests/fixtures/invalid_places.json tests/fixtures/

# Move conftest
git mv apps/api/tests/conftest.py tests/conftest.py
```

**Step 2: Create `__init__.py` files for test subdirectories**

Create empty `__init__.py` in each test subdirectory so pytest discovers them:

```
tests/api/__init__.py
tests/domain/__init__.py
tests/content/__init__.py
tests/journal/__init__.py
tests/persistence/__init__.py
tests/player/__init__.py
tests/assets/__init__.py
```

**Step 3: Commit**

```bash
git add tests/ apps/api/tests/
git commit -m "refactor: move tests to mirrored structure at repo root"
```

---

### Task 4: Update all imports in tests

**Files:**
- Modify: every `.py` file under `tests/`

**Step 1: Replace all imports in test files**

In every `.py` file under `tests/`, replace:
- `from app.` → `from idle_chapters.`
- `import app.` → `import idle_chapters.`

Files with imports to change:

```
tests/api/test_api.py
tests/domain/test_engine.py
tests/domain/test_effects.py
tests/domain/test_conditions.py
tests/domain/test_scene_generation.py
tests/content/test_content_loader.py
tests/content/test_content_manifest.py
tests/content/test_content_repo.py
tests/content/test_validators.py
tests/journal/test_journal_renderer.py
tests/persistence/test_persistence.py
tests/player/test_player.py
tests/player/test_player_schema.py
tests/assets/test_backfill_assets.py
tests/assets/test_update_assets.py
```

**Step 2: Update conftest.py**

Replace `tests/conftest.py` — the `sys.path` manipulation is no longer needed:

```python
# tests/conftest.py
import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def disable_otel() -> None:
    os.environ.setdefault("OTEL_DISABLED", "true")
```

**Step 3: Update fixture path references**

Some tests reference fixture files relative to their old location. Search for `fixtures/` path references in test files and update them to use a conftest fixture or `Path(__file__).parent.parent / "fixtures"`.

Add to `tests/conftest.py`:

```python
from pathlib import Path


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / ".git").is_dir():
            return parent
    return path.parents[1]
```

**Step 4: Commit**

```bash
git add tests/
git commit -m "refactor: update test imports and simplify conftest"
```

---

### Task 5: Update configuration files

**Files:**
- Modify: `pytest.ini`
- Move: `apps/api/pyproject.toml` → `pyproject.toml` (repo root, merge if needed)
- Move: `apps/api/requirements.txt` → `requirements.txt` (repo root)
- Move: `apps/api/Dockerfile` → `Dockerfile` (repo root)
- Delete: `apps/api/PYTHONPATH`
- Modify: `.github/workflows/api.yml`

**Step 1: Update pytest.ini**

Replace contents of `pytest.ini`:

```ini
[pytest]
testpaths = tests
addopts = -ra
env =
    OTEL_SDK_DISABLED=true
```

**Step 2: Move pyproject.toml**

```bash
git mv apps/api/pyproject.toml pyproject.toml
```

If `pyproject.toml` already exists at root, merge the content. The key field is `requires-python = ">=3.12"`.

**Step 3: Move requirements.txt**

A `requirements.txt` may already exist at root. If so, replace it with the one from `apps/api/`:

```bash
git mv apps/api/requirements.txt requirements.txt
```

**Step 4: Move and update Dockerfile**

```bash
git mv apps/api/Dockerfile Dockerfile
```

Update `Dockerfile` contents:

```dockerfile
FROM python:3.12-slim

WORKDIR /idle_chapters_app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY idle_chapters ./idle_chapters
COPY assets ./assets
COPY schemas ./schemas
COPY lexicons ./lexicons

EXPOSE 8000

CMD ["uvicorn", "idle_chapters.api.server:server", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 5: Delete PYTHONPATH file**

```bash
git rm apps/api/PYTHONPATH
```

**Step 6: Update CI workflow**

Replace `.github/workflows/api.yml`:

```yaml
name: API CI

on:
  push:
    paths:
      - 'idle_chapters/**'
      - 'tests/**'
      - 'assets/**'
      - 'schemas/**'
      - 'requirements.txt'
  pull_request:
    paths:
      - 'idle_chapters/**'
      - 'tests/**'
      - 'assets/**'
      - 'schemas/**'
      - 'requirements.txt'

jobs:
  ci:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
          cache-dependency-path: requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest
```

**Step 7: Commit**

```bash
git add pytest.ini pyproject.toml requirements.txt Dockerfile .github/workflows/api.yml
git rm apps/api/PYTHONPATH
git commit -m "refactor: move config files to repo root and update CI"
```

---

### Task 6: Clean up and verify

**Files:**
- Delete: `apps/api/` (should be empty now except `apps/web/`)
- Modify: `design-docs/plans/2026-04-04-structured-errors-plan.md` (update imports)

**Step 1: Verify apps/api/ is empty**

```bash
find apps/api/ -type f -not -path "*__pycache__*" 2>/dev/null
```

Expected: no output (all files moved). If any remain, move them.

```bash
rm -rf apps/api/
```

Note: `apps/web/` must remain untouched.

**Step 2: Verify no `from app.` imports remain**

```bash
grep -rn "from app\.\|import app\." idle_chapters/ tests/ --include="*.py"
```

Expected: no output.

**Step 3: Run the full test suite**

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/persistence/test_persistence.py
```

Expected: 93+ passed.

**Step 4: Verify the app starts**

```bash
.venv/bin/python -m idle_chapters 2>&1 | head -1
```

Expected: CLI starts (will print the welcome text).

```bash
.venv/bin/python -c "from idle_chapters.api.server import server; print(server.title)"
```

Expected: `Idle Chapters API`

**Step 5: Update structured errors plan imports**

In `design-docs/plans/2026-04-04-structured-errors-plan.md`, replace all:
- `from app.` → `from idle_chapters.`
- `apps/api/app/` → `idle_chapters/`
- `apps/api/tests/` → `tests/`

**Step 6: Final commit**

```bash
git add -A  # safe here — we're cleaning up, not adding new code
git commit -m "refactor: clean up empty apps/api/ and update structured errors plan"
```

**Step 7: Run tests one final time**

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/persistence/test_persistence.py
```

Expected: all pass.
