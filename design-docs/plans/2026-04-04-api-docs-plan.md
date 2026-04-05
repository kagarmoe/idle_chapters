# API Documentation Examples Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OpenAPI examples with real game data to all API endpoints — success responses on models, error responses on routes, and usage snippets in descriptions.

**Architecture:** Success examples via Pydantic `model_config`. Error examples via FastAPI `responses` parameter on route decorators. Usage snippets as markdown in endpoint `description` strings. All data sourced from `assets/`.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2.12

**Design doc:** `design-docs/plans/2026-04-04-api-docs-design.md`

---

### Task 1: Add success examples to Pydantic models

**Files:**
- Modify: `idle_chapters/api/models.py`

**Step 1: Add examples to response models**

Read `idle_chapters/api/models.py`. Add `model_config = ConfigDict(json_schema_extra={"example": ...})` to these models. Import `ConfigDict` from `pydantic` if not already imported.

```python
from pydantic import BaseModel, ConfigDict, Field
```

**ViewAction:**
```python
class ViewAction(BaseModel):
    action_id: str
    label: str

    model_config = ConfigDict(json_schema_extra={"example": {
        "action_id": "rest_longer",
        "label": "Rest a bit longer",
    }})
```

**ViewModel:**
```python
class ViewModel(BaseModel):
    prompt: str | None = None
    scene_id: str | None = None
    eligible_actions: list[ViewAction] = Field(default_factory=list)
    visible_items: list[str] = Field(default_factory=list)
    visible_npcs: list[str] = Field(default_factory=list)

    model_config = ConfigDict(json_schema_extra={"example": {
        "prompt": "The cottage rests in a quiet countryside, with a thatched roof and smoke curling from the chimney.",
        "scene_id": "cottage_home_tea_arrival_42",
        "eligible_actions": [
            {"action_id": "rest_longer", "label": "Rest a bit longer"},
            {"action_id": "cottage_wake", "label": "Wake in the cottage"},
        ],
        "visible_items": [],
        "visible_npcs": ["npc_baker_elin"],
    }})
```

**SessionCreateResponse:**
```python
    model_config = ConfigDict(json_schema_extra={"example": {
        "session_id": "a1b2c3d4e5f67890abcdef1234567890",
        "view": {
            "prompt": "The cottage rests in a quiet countryside, with a thatched roof and smoke curling from the chimney.",
            "scene_id": "cottage_home_tea_arrival_42",
            "eligible_actions": [
                {"action_id": "rest_longer", "label": "Rest a bit longer"},
                {"action_id": "cottage_wake", "label": "Wake in the cottage"},
            ],
            "visible_items": [],
            "visible_npcs": [],
        },
        "journal_page": {
            "page_id": "jp-a1b2c3",
            "place_id": "cottage_home",
            "entry_type": "tea",
            "mood": "Home",
            "need": "Permission to rest and recover",
            "body": "The kettle sang softly. You watched the steam curl and disappear.",
        },
    }})
```

**SessionGetResponse:**
```python
    model_config = ConfigDict(json_schema_extra={"example": {
        "session_id": "a1b2c3d4e5f67890abcdef1234567890",
        "view": {
            "prompt": None,
            "scene_id": None,
            "eligible_actions": [],
            "visible_items": [],
            "visible_npcs": [],
        },
        "state": {
            "current_place_id": "cottage_home",
            "inventory": {"chamomile": 2, "black_tea": 1},
            "flags": ["visited_forest"],
            "time_tick": 5,
        },
    }})
```

**StepResponse:**
```python
    model_config = ConfigDict(json_schema_extra={"example": {
        "view": {
            "prompt": "You stay tucked into the comfort of your cottage. Light drifts through the window.",
            "scene_id": "cottage_home_tea_arrival_42",
            "eligible_actions": [
                {"action_id": "cottage_wake", "label": "Wake in the cottage"},
            ],
            "visible_items": [],
            "visible_npcs": [],
        },
        "journal_page": {
            "page_id": "jp-d4e5f6",
            "place_id": "cottage_home",
            "entry_type": "tea",
            "mood": "Home",
            "need": "Permission to rest and recover",
            "body": "A thin curl of steam rises. Nothing needs to happen yet.",
        },
        "choices": [
            {"action_id": "cottage_wake", "label": "Wake in the cottage"},
        ],
    }})
```

**PlayerResponse:**
```python
    model_config = ConfigDict(json_schema_extra={"example": {
        "player_id": "f1e2d3c4b5a67890abcdef1234567890",
        "player_info": {
            "display_name": "Wanderer",
            "pronouns": "they/them",
        },
        "state": {
            "current_location": "cottage_home",
            "inventory_counts": {"chamomile": 2},
            "visit_counts": {"cottage_home": 3},
            "seen_interactions": {},
            "flags": ["visited_forest"],
        },
    }})
```

**Step 2: Verify examples render**

```bash
.venv/bin/python -c "from idle_chapters.api.server import server; print('Models load OK')"
```

**Step 3: Commit**

```bash
git add idle_chapters/api/models.py
git commit -m "docs: add success examples to Pydantic response models

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Add error examples to session routes

**Files:**
- Modify: `idle_chapters/api/routers/sessions.py`

**Step 1: Define reusable error response dicts**

At the top of the file (after imports), define error response examples that will be used in route decorators. This avoids duplicating the same 404 example on every endpoint.

```python
_SESSION_NOT_FOUND_RESPONSES = {
    404: {
        "description": "Session not found",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:session_not_found",
                            "title": "That story has found its own ending. You're welcome to begin a new one whenever you'd like.",
                            "status": 404,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:session_not_found",
                            "title": "Session Not Found",
                            "status": 404,
                            "detail": "WHAT: No session exists for abc123.\nMEANS: Nothing was modified.\nDO: Create a new session via POST /v1/sessions.",
                            "instance": "urn:idle-chapters:occurrence:a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "effect": "none",
                            "recovery": "terminal",
                            "signal": "NOTICE",
                            "context": {"session_id": "abc123"},
                        },
                    },
                },
            },
        },
    },
}

_ACTION_NOT_ELIGIBLE_RESPONSE = {
    409: {
        "description": "Action not eligible for current state",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:action_not_eligible",
                            "title": "That doesn't seem possible right now. Maybe explore a bit more first.",
                            "status": 409,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:action_not_eligible",
                            "title": "Action Not Eligible",
                            "status": 409,
                            "detail": "WHAT: Action gather_herbs failed conditions for session abc123.\nMEANS: State unchanged. Action requires unmet conditions.\nDO: Check eligible actions via GET /v1/sessions/abc123.",
                            "instance": "urn:idle-chapters:occurrence:b2c3d4e5-f6a7-8901-bcde-f12345678901",
                            "effect": "none",
                            "recovery": "correctable",
                            "signal": "CAUTION",
                            "context": {"action_id": "gather_herbs", "session_id": "abc123", "unmet": ["flags_set: visited_garden"]},
                        },
                    },
                },
            },
        },
    },
}

_INTENT_NO_MATCH_RESPONSE = {
    422: {
        "description": "No action matched the free-text intent",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:intent_no_match",
                            "title": "I didn't quite catch that. What would you like to do?",
                            "status": 422,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:intent_no_match",
                            "title": "Intent No Match",
                            "status": 422,
                            "detail": "WHAT: No action matched intent 'fly away' for session abc123.\nMEANS: State unchanged. Available actions: ['Rest a bit longer', 'Wake in the cottage'].\nDO: Rephrase or choose from eligible actions.",
                            "instance": "urn:idle-chapters:occurrence:c3d4e5f6-a7b8-9012-cdef-123456789012",
                            "effect": "none",
                            "recovery": "correctable",
                            "signal": "CAUTION",
                            "context": {"input": "fly away", "available_actions": "Rest a bit longer, Wake in the cottage", "session_id": "abc123"},
                        },
                    },
                },
            },
        },
    },
}
```

**Step 2: Add responses to route decorators**

Add `responses={...}` to each endpoint that can fail. Merge dicts for endpoints with multiple error types:

- `GET /{session_id}` — `responses=_SESSION_NOT_FOUND_RESPONSES`
- `POST /{session_id}/enter` — `responses=_SESSION_NOT_FOUND_RESPONSES`
- `POST /{session_id}/action` — `responses={**_SESSION_NOT_FOUND_RESPONSES, **_ACTION_NOT_ELIGIBLE_RESPONSE}`
- `POST /{session_id}/intent` — `responses={**_SESSION_NOT_FOUND_RESPONSES, **_INTENT_NO_MATCH_RESPONSE}`
- `GET /{session_id}/journal` — `responses=_SESSION_NOT_FOUND_RESPONSES`
- `GET /{session_id}/journal/{page_id}` — `responses=_SESSION_NOT_FOUND_RESPONSES`

**Step 3: Add usage descriptions to key endpoints**

Add a `description` parameter with curl/Python snippets to the most important endpoints:

For `POST /v1/sessions` (create_session):
```python
@router.post("", response_model=SessionCreateResponse, description="""
Create a new game session and enter the starting location.

**curl:**
```bash
curl -X POST http://localhost:8000/v1/sessions \\
  -H "Content-Type: application/json" \\
  -d '{"place_id": "cottage_home"}'
```

**Python (httpx):**
```python
import httpx
resp = httpx.post("http://localhost:8000/v1/sessions", json={"place_id": "cottage_home"})
session = resp.json()
```
""")
```

For `POST /{session_id}/action` (submit_action):
```python
description="""
Execute a chosen action in the current scene.

**curl:**
```bash
curl -X POST http://localhost:8000/v1/sessions/{session_id}/action \\
  -H "Content-Type: application/json" \\
  -d '{"action_id": "rest_longer"}'
```

To see developer error details, add the projection header:
```bash
curl -H "Accept-Projection: developer" ...
```
"""
```

Add similar descriptions to `POST /{session_id}/intent` and `GET /{session_id}`.

**Step 4: Commit**

```bash
git add idle_chapters/api/routers/sessions.py
git commit -m "docs: add error examples and usage snippets to session routes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Add error examples to player and journal routes

**Files:**
- Modify: `idle_chapters/api/routers/players.py`
- Modify: `idle_chapters/api/routers/journal.py`

**Step 1: Add error response dict to players.py**

At the top of `players.py` (after imports):

```python
_PLAYER_NOT_FOUND_RESPONSES = {
    404: {
        "description": "Player not found",
        "content": {
            "application/json": {
                "examples": {
                    "player": {
                        "summary": "Player projection (default)",
                        "value": {
                            "type": "urn:idle-chapters:error:player_not_found",
                            "title": "That traveler doesn't seem to be around. Perhaps they've wandered somewhere new.",
                            "status": 404,
                        },
                    },
                    "developer": {
                        "summary": "Developer projection (Accept-Projection: developer)",
                        "value": {
                            "type": "urn:idle-chapters:error:player_not_found",
                            "title": "Player Not Found",
                            "status": 404,
                            "detail": "WHAT: No player exists for f1e2d3c4.\nMEANS: Nothing was modified.\nDO: Create a new player via POST /v1/players.",
                            "instance": "urn:idle-chapters:occurrence:d4e5f6a7-b8c9-0123-defa-234567890123",
                            "effect": "none",
                            "recovery": "terminal",
                            "signal": "NOTICE",
                            "context": {"player_id": "f1e2d3c4"},
                        },
                    },
                },
            },
        },
    },
}
```

**Step 2: Add responses to player route decorators**

- `GET /{player_id}` — `responses=_PLAYER_NOT_FOUND_RESPONSES`
- `PATCH /{player_id}` — `responses=_PLAYER_NOT_FOUND_RESPONSES`

Add a usage description to `POST /v1/players`:
```python
description="""
Create a new player profile.

**curl:**
```bash
curl -X POST http://localhost:8000/v1/players \\
  -H "Content-Type: application/json" \\
  -d '{"display_name": "Wanderer", "pronouns_key": "they/them"}'
```
"""
```

**Step 3: Update journal.py**

Import the response dict from players (or define locally if import is awkward):

```python
from idle_chapters.api.routers.players import _PLAYER_NOT_FOUND_RESPONSES
```

Wait — this would be another cross-module private import. Better: move `_PLAYER_NOT_FOUND_RESPONSES` to `error_helpers.py` alongside `raise_player_not_found`, and rename it to `PLAYER_NOT_FOUND_RESPONSES` (drop underscore). Then both routers import from there.

Add `responses=PLAYER_NOT_FOUND_RESPONSES` to both journal endpoints.

**Step 4: Commit**

```bash
git add idle_chapters/api/routers/players.py idle_chapters/api/routers/journal.py idle_chapters/api/routers/error_helpers.py
git commit -m "docs: add error examples to player and journal routes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Add examples to world routes

**Files:**
- Modify: `idle_chapters/api/routers/world.py`

**Step 1: Add response examples and descriptions**

The world routes are read-only and return raw dicts, so examples go on the route decorators via `response_description` and inline `responses` for the 200 case.

Add a usage description to `GET /v1/world/manifest`:
```python
@router.get("/manifest", description="""
Return metadata about all game content: schemas, assets, and lexicons.

**curl:**
```bash
curl http://localhost:8000/v1/world/manifest
```
""")
```

For list endpoints (`places`, `scenes`, `actions`, `collectibles`, `npcs`), add brief descriptions noting what they return. No error examples needed.

**Step 2: Commit**

```bash
git add idle_chapters/api/routers/world.py
git commit -m "docs: add descriptions to world routes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Regenerate OpenAPI spec and verify

**Files:**
- Modify: `docs/openapi.json`

**Step 1: Regenerate the spec**

```bash
.venv/bin/python -c "
from idle_chapters.api.server import create_app
import json
from pathlib import Path
app = create_app()
spec = app.openapi()
Path('docs/openapi.json').write_text(json.dumps(spec, indent=2))
print('Regenerated')
"
```

**Step 2: Run the full test suite**

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/persistence/ -q
```

Expected: 140 passed.

**Step 3: Visually verify in Swagger UI**

```bash
.venv/bin/uvicorn idle_chapters.api.server:server --port 8000 &
# Open http://localhost:8000/docs in browser
# Check: examples appear on response schemas, error examples show both projections
# Kill the server when done
kill %1
```

**Step 4: Commit**

```bash
git add docs/openapi.json
git commit -m "docs: regenerate OpenAPI spec with examples

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```
