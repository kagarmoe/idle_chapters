# M6: FastAPI v1 — Implementation Plan

> **For Claude:**

**Goal:** Wire FastAPI endpoints to the domain engine through a `SessionService`, making the game playable via HTTP.

**Architecture:** Thin `SessionService` bridge (plain Python, no FastAPI imports) between routers and `Engine.step()`. Routers validate requests and format responses. Persistence via M5 stores (`StateStore`, `JournalStore`, `EventStore`). Tests use in-memory store stubs.

**Tech Stack:** Python 3.10+, FastAPI, pytest, dataclasses

---

### Task 1: Update Response Models (`app/api/models.py`)

**Files:**
- Modify: `app/api/models.py`

**Step 1: Update models**

Replace the current `StepResponse` and `SessionResponse` and add `StepResponseModel` / `SessionCreateResponse`. Drop unused `state_delta`, `applied_actions`. Add `journal_page` and `choices`.

Replace the full file content with:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ViewAction(BaseModel):
    action_id: str
    label: str


class ViewModel(BaseModel):
    prompt: str | None = None
    scene_id: str | None = None
    eligible_actions: list[ViewAction] = Field(default_factory=list)
    visible_items: list[str] = Field(default_factory=list)
    visible_npcs: list[str] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    place_id: str = "cottage_home"


class IntentRequest(BaseModel):
    input: str


class ActionRequest(BaseModel):
    action_id: str


class SessionCreateResponse(BaseModel):
    session_id: str
    view: ViewModel
    journal_page: dict | None = None


class SessionGetResponse(BaseModel):
    session_id: str
    view: ViewModel
    state: dict | None = None


class StepResponse(BaseModel):
    view: ViewModel
    journal_page: dict | None = None
    choices: list[ViewAction] = Field(default_factory=list)


class PlayerInfo(BaseModel):
    display_name: str | None = None
    pronouns: str | None = None


class PlayerState(BaseModel):
    current_location: str | None = None
    inventory_counts: dict[str, int] = Field(default_factory=dict)
    visit_counts: dict[str, int] = Field(default_factory=dict)
    seen_interactions: dict[str, Any] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)


class PlayerCreateRequest(BaseModel):
    display_name: str | None = None
    pronouns_key: str | None = None


class PlayerUpdateRequest(BaseModel):
    display_name: str | None = None
    pronouns_key: str | None = None


class PlayerResponse(BaseModel):
    player_id: str
    player_info: PlayerInfo | None = None
    state: PlayerState | None = None
```

Key changes from current file:
- `SessionCreateRequest` now takes `place_id` instead of `player_id`
- New `SessionCreateResponse` with `session_id`, `view`, `journal_page`
- New `SessionGetResponse` with `session_id`, `view`, `state`
- `StepResponse` replaced: now has `view`, `journal_page`, `choices` (dropped `applied_actions`, `state_delta`, `journal_entries`)
- Removed `SessionResponse` (replaced by the two new response models)

**Step 2: Commit**

```bash
git add app/api/models.py
git commit -m "refactor(api): Update response models for M6 engine integration"
```

---

### Task 2: SessionService — Failing Tests

**Files:**
- Modify: `tests/test_api.py`

**Step 1: Write SessionService unit tests**

Replace the entire file. These tests use in-memory stub stores and a real `ContentRepo` + `Engine`, exercising `SessionService` methods directly (no HTTP).

```python
from __future__ import annotations

import pytest

from idle_chapters.content.repo import ContentRepo
from idle_chapters.domain.engine import Engine
from idle_chapters.domain.state import PlayerState


class StubStateStore:
    """In-memory StateStore stub for testing."""

    def __init__(self):
        self._data: dict[str, PlayerState] = {}

    def upsert_state(self, session_id: str, state: PlayerState) -> None:
        self._data[session_id] = state

    def get_state(self, session_id: str) -> PlayerState | None:
        return self._data.get(session_id)


class StubJournalStore:
    """In-memory JournalStore stub for testing."""

    def __init__(self):
        self._pages: dict[str, list[dict]] = {}

    def append_page(self, session_id: str, page: dict) -> None:
        self._pages.setdefault(session_id, []).append(page)

    def list_pages(self, session_id: str) -> list[dict]:
        return self._pages.get(session_id, [])

    def get_page(self, session_id: str, page_id: str) -> dict | None:
        for p in self._pages.get(session_id, []):
            if p.get("page_id") == page_id:
                return p
        return None


class StubEventStore:
    """In-memory EventStore stub for testing."""

    def __init__(self):
        self._events: dict[str, list[dict]] = {}

    def append_event(self, session_id: str, event: dict) -> None:
        self._events.setdefault(session_id, []).append(event)

    def list_events(self, session_id: str) -> list[dict]:
        return self._events.get(session_id, [])


@pytest.fixture
def repo():
    return ContentRepo()


@pytest.fixture
def stores():
    return StubStateStore(), StubJournalStore(), StubEventStore()


@pytest.fixture
def service(repo, stores):
    from idle_chapters.services.session_service import SessionService

    state_store, journal_store, event_store = stores
    return SessionService(
        repo=repo,
        engine=Engine(),
        state_store=state_store,
        journal_store=journal_store,
        event_store=event_store,
    )


def test_create_session_returns_session_id_and_journal_page(service) -> None:
    session_id, result = service.create_session()
    assert session_id is not None
    assert len(session_id) > 0
    assert result.journal_page is not None
    assert result.new_state.current_place_id == "cottage_home"


def test_create_session_persists_state(service, stores) -> None:
    state_store, journal_store, _ = stores
    session_id, _ = service.create_session()
    loaded = state_store.get_state(session_id)
    assert loaded is not None
    assert loaded.current_place_id == "cottage_home"
    assert journal_store.list_pages(session_id)


def test_perform_action_returns_updated_state(service) -> None:
    session_id, result = service.create_session()
    choices = result.choices
    if not choices:
        pytest.skip("No choices available from initial scene")
    action_id = choices[0]["action_id"]
    step_result = service.perform_action(session_id, action_id)
    assert step_result.journal_page is not None


def test_get_session_returns_state(service) -> None:
    session_id, _ = service.create_session()
    state = service.get_session(session_id)
    assert state is not None
    assert state.session_id == session_id
    assert state.current_place_id == "cottage_home"


def test_get_session_missing_returns_none(service) -> None:
    assert service.get_session("nonexistent") is None


def test_enter_returns_choices(service) -> None:
    session_id, _ = service.create_session()
    result = service.enter(session_id)
    assert result.choices is not None
    assert result.journal_page is not None


def test_submit_intent_matches_action(service) -> None:
    session_id, result = service.create_session()
    choices = result.choices
    if not choices:
        pytest.skip("No choices available from initial scene")
    # Use the label of the first choice as intent text
    label = choices[0].get("label", "")
    step_result = service.submit_intent(session_id, label)
    assert step_result.journal_page is not None


def test_state_persists_across_calls(service, stores) -> None:
    state_store, _, _ = stores
    session_id, result = service.create_session()
    choices = result.choices
    if not choices:
        pytest.skip("No choices available")
    action_id = choices[0]["action_id"]
    service.perform_action(session_id, action_id)
    loaded = state_store.get_state(session_id)
    assert loaded is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api.py -v`
Expected: FAIL — `SessionService` has no real methods (stub file)

**Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "test(api): Rewrite test_api.py with SessionService unit tests"
```

---

### Task 3: SessionService — Implementation

**Files:**
- Modify: `app/services/session_service.py`

**Step 1: Implement SessionService**

```python
from __future__ import annotations

from uuid import uuid4

from idle_chapters.domain.engine import Engine
from idle_chapters.domain.state import PlayerState
from idle_chapters.domain.step_result import StepResult


class SessionService:
    """Bridge between API routers (or CLI) and the domain engine.

    Plain Python — no FastAPI imports. Reusable by any interface.
    """

    def __init__(self, repo, engine: Engine, state_store, journal_store, event_store):
        self._repo = repo
        self._engine = engine
        self._state_store = state_store
        self._journal_store = journal_store
        self._event_store = event_store

    def create_session(self, place_id: str = "cottage_home") -> tuple[str, StepResult]:
        """Create a new session and enter the starting place."""
        session_id = uuid4().hex

        state = PlayerState(
            session_id=session_id,
            current_place_id=place_id,
            inventory={},
            flags=set(),
            time_tick=0,
        )

        result = self._engine.step(state, "enter", None, self._repo)
        self._persist(session_id, result)

        return session_id, result

    def enter(self, session_id: str) -> StepResult:
        """Re-enter the current place (refresh scene)."""
        state = self._load_state(session_id)
        result = self._engine.step(state, "enter", None, self._repo)
        self._persist(session_id, result)
        return result

    def perform_action(self, session_id: str, action_id: str) -> StepResult:
        """Execute a chosen action."""
        state = self._load_state(session_id)
        result = self._engine.step(state, "choose option", action_id, self._repo)
        self._persist(session_id, result)
        return result

    def submit_intent(self, session_id: str, text: str) -> StepResult:
        """Match free-text input to an eligible action and execute it."""
        state = self._load_state(session_id)

        # Get current choices to match against
        current_result = self._engine.step(state, "enter", None, self._repo)
        matched_id = self._match_intent(text, current_result.choices)

        if matched_id is None:
            raise ValueError(f"No eligible action matched intent: {text!r}")

        result = self._engine.step(state, "choose option", matched_id, self._repo)
        self._persist(session_id, result)
        return result

    def get_session(self, session_id: str) -> PlayerState | None:
        """Load and return current player state, or None if not found."""
        return self._state_store.get_state(session_id)

    def _load_state(self, session_id: str) -> PlayerState:
        state = self._state_store.get_state(session_id)
        if state is None:
            raise ValueError(f"Session not found: {session_id}")
        return state

    def _persist(self, session_id: str, result: StepResult) -> None:
        self._state_store.upsert_state(session_id, result.new_state)

        if result.journal_page:
            self._journal_store.append_page(session_id, result.journal_page)

        self._event_store.append_event(session_id, {
            "event_type": "step",
            "data": {
                "scene_id": result.debug.get("selected_scene_id") if result.debug else None,
                "choice_id": result.debug.get("choice_id") if result.debug else None,
            },
        })

    @staticmethod
    def _match_intent(text: str, choices: list[dict]) -> str | None:
        """Match free-text input against choice labels and action intent signatures."""
        text_lower = text.lower()
        for choice in choices:
            label = choice.get("label", "").lower()
            if label and label in text_lower:
                return choice["action_id"]
        return None
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`
Expected: 8 PASSED

**Step 3: Commit**

```bash
git add app/services/session_service.py
git commit -m "feat(api): Implement SessionService bridge to domain engine"
```

---

### Task 4: Dependency Injection Setup

**Files:**
- Modify: `app/api/deps.py`

**Step 1: Add SessionService dependency**

Add a `get_session_service()` dependency that creates a `SessionService` with real persistence stores. The existing `get_content_repo()` and `get_db()` stay untouched.

```python
from __future__ import annotations

from pymongo.database import Database

from idle_chapters.api.db import get_db as _get_db
from idle_chapters.content.repo import ContentRepo
from idle_chapters.domain.engine import Engine
from idle_chapters.services.session_service import SessionService


CONTENT_REPO = ContentRepo()

_ENGINE = Engine()


def get_content_repo() -> ContentRepo:
    return CONTENT_REPO


def get_db() -> Database:
    return _get_db()


def get_session_service() -> SessionService:
    from idle_chapters.persistence.event_store import EventStore
    from idle_chapters.persistence.journal_store import JournalStore
    from idle_chapters.persistence.state_store import StateStore

    return SessionService(
        repo=CONTENT_REPO,
        engine=_ENGINE,
        state_store=StateStore(),
        journal_store=JournalStore(),
        event_store=EventStore(),
    )
```

**Step 2: Commit**

```bash
git add app/api/deps.py
git commit -m "feat(api): Add SessionService dependency injection"
```

---

### Task 5: Rewrite Sessions Router

**Files:**
- Modify: `app/api/routers/sessions.py`

**Step 1: Rewrite the router**

Replace the entire file. The router is now thin — validates request, calls `SessionService`, formats response. All business logic lives in `SessionService`.

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from idle_chapters.api.deps import get_session_service
from idle_chapters.api.models import (
    ActionRequest,
    IntentRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionGetResponse,
    StepResponse,
    ViewAction,
    ViewModel,
)
from idle_chapters.domain.step_result import StepResult
from idle_chapters.services.session_service import SessionService

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


def _view_from_result(result: StepResult) -> ViewModel:
    """Build a ViewModel from a StepResult."""
    prompt = None
    if result.journal_page:
        prompt = result.journal_page.get("body") or result.journal_page.get("prompt")

    return ViewModel(
        prompt=prompt,
        scene_id=result.debug.get("selected_scene_id") if result.debug else None,
        eligible_actions=[
            ViewAction(action_id=c["action_id"], label=c.get("label", c["action_id"]))
            for c in result.choices
        ],
    )


def _step_response(result: StepResult) -> StepResponse:
    """Build a StepResponse from a StepResult."""
    view = _view_from_result(result)
    return StepResponse(
        view=view,
        journal_page=result.journal_page,
        choices=view.eligible_actions,
    )


@router.post("", response_model=SessionCreateResponse)
def create_session(
    request: SessionCreateRequest = None,
    service: SessionService = Depends(get_session_service),
) -> SessionCreateResponse:
    place_id = request.place_id if request else "cottage_home"
    session_id, result = service.create_session(place_id=place_id)
    view = _view_from_result(result)
    return SessionCreateResponse(
        session_id=session_id,
        view=view,
        journal_page=result.journal_page,
    )


@router.get("/{session_id}", response_model=SessionGetResponse)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionGetResponse:
    state = service.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionGetResponse(
        session_id=session_id,
        view=ViewModel(),
        state={
            "current_place_id": state.current_place_id,
            "inventory": state.inventory,
            "flags": sorted(state.flags),
            "time_tick": state.time_tick,
        },
    )


@router.post("/{session_id}/enter", response_model=StepResponse)
def enter_place(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    try:
        result = service.enter(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _step_response(result)


@router.post("/{session_id}/action", response_model=StepResponse)
def submit_action(
    session_id: str,
    request: ActionRequest,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    try:
        result = service.perform_action(session_id, request.action_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _step_response(result)


@router.post("/{session_id}/intent", response_model=StepResponse)
def submit_intent(
    session_id: str,
    request: IntentRequest,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    try:
        result = service.submit_intent(session_id, request.input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _step_response(result)
```

**Step 2: Commit**

```bash
git add app/api/routers/sessions.py
git commit -m "refactor(api): Rewrite sessions router to delegate to SessionService"
```

---

### Task 6: Session-Scoped Journal Endpoints

**Files:**
- Modify: `app/api/routers/sessions.py`

**Step 1: Add journal endpoints to sessions router**

Append these two endpoints to the end of `app/api/routers/sessions.py`:

```python
@router.get("/{session_id}/journal")
def list_journal_pages(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> list[dict]:
    state = service.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return service._journal_store.list_pages(session_id)


@router.get("/{session_id}/journal/{page_id}")
def get_journal_page(
    session_id: str,
    page_id: str,
    service: SessionService = Depends(get_session_service),
) -> dict:
    state = service.get_session(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    page = service._journal_store.get_page(session_id, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Journal page not found")
    return page
```

**Step 2: Add journal tests to test_api.py**

Append to `tests/test_api.py`:

```python
def test_journal_list_returns_pages(service, stores) -> None:
    _, journal_store, _ = stores
    session_id, _ = service.create_session()
    pages = journal_store.list_pages(session_id)
    assert len(pages) >= 1


def test_journal_get_missing_returns_none(service, stores) -> None:
    _, journal_store, _ = stores
    session_id, _ = service.create_session()
    assert journal_store.get_page(session_id, "nonexistent") is None
```

**Step 3: Run tests**

Run: `pytest tests/test_api.py -v`
Expected: 10 PASSED

**Step 4: Commit**

```bash
git add app/api/routers/sessions.py tests/test_api.py
git commit -m "feat(api): Add session-scoped journal endpoints"
```

---

### Task 7: HTTP Integration Tests

**Files:**
- Modify: `tests/test_api.py`

**Step 1: Add HTTP-level tests using TestClient**

These tests exercise the full FastAPI stack with dependency overrides. Append to `tests/test_api.py`:

```python
from fastapi.testclient import TestClient


@pytest.fixture
def client(repo, stores):
    from idle_chapters.api.app import create_app
    from idle_chapters.api.deps import get_session_service

    state_store, journal_store, event_store = stores

    app = create_app()

    def _override_service():
        return SessionService(
            repo=repo,
            engine=Engine(),
            state_store=state_store,
            journal_store=journal_store,
            event_store=event_store,
        )

    app.dependency_overrides[get_session_service] = _override_service
    return TestClient(app)


def test_http_create_session(client) -> None:
    response = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "view" in data
    assert "journal_page" in data


def test_http_get_session(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.get(f"/v1/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "state" in data


def test_http_get_session_not_found(client) -> None:
    response = client.get("/v1/sessions/nonexistent")
    assert response.status_code == 404


def test_http_enter(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.post(f"/v1/sessions/{session_id}/enter")
    assert response.status_code == 200
    data = response.json()
    assert "view" in data
    assert "choices" in data


def test_http_action(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    enter = client.post(f"/v1/sessions/{session_id}/enter")
    choices = enter.json().get("choices", [])
    if not choices:
        pytest.skip("No choices available")
    action_id = choices[0]["action_id"]
    response = client.post(
        f"/v1/sessions/{session_id}/action",
        json={"action_id": action_id},
    )
    assert response.status_code == 200
    assert "journal_page" in response.json()


def test_http_intent(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    enter = client.post(f"/v1/sessions/{session_id}/enter")
    choices = enter.json().get("choices", [])
    if not choices:
        pytest.skip("No choices available")
    label = choices[0]["label"]
    response = client.post(
        f"/v1/sessions/{session_id}/intent",
        json={"input": label},
    )
    assert response.status_code == 200


def test_http_journal_list(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]
    response = client.get(f"/v1/sessions/{session_id}/journal")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_http_state_persists_across_calls(client) -> None:
    create = client.post("/v1/sessions", json={"place_id": "cottage_home"})
    session_id = create.json()["session_id"]

    enter = client.post(f"/v1/sessions/{session_id}/enter")
    choices = enter.json().get("choices", [])
    if not choices:
        pytest.skip("No choices available")
    action_id = choices[0]["action_id"]
    client.post(f"/v1/sessions/{session_id}/action", json={"action_id": action_id})

    state_response = client.get(f"/v1/sessions/{session_id}")
    assert state_response.status_code == 200
    assert state_response.json()["session_id"] == session_id
```

**Step 2: Run all tests**

Run: `pytest tests/test_api.py -v`
Expected: 19 PASSED (8 service + 2 journal + 9 HTTP)

**Step 3: Commit**

```bash
git add tests/test_api.py
git commit -m "test(api): Add HTTP integration tests with TestClient"
```

---

### Task 8: Full Suite Verification

**Step 1: Run all API tests**

Run: `pytest tests/test_api.py -v`
Expected: 19 PASSED

**Step 2: Run full test suite for regressions**

Run: `pytest tests/ --ignore=tests/test_persistence.py -v`
Expected: No regressions. Persistence tests ignored (require MONGO_URL).

**Step 3: Verify Swagger docs load**

Run: `python -c "from idle_chapters.api.app import create_app; app = create_app(); print([r.path for r in app.routes])"`
Expected: Shows `/v1/sessions`, `/v1/sessions/{session_id}`, `/v1/sessions/{session_id}/enter`, `/v1/sessions/{session_id}/action`, `/v1/sessions/{session_id}/intent`, `/v1/sessions/{session_id}/journal`, `/v1/sessions/{session_id}/journal/{page_id}`

**Step 4: Final commit with all files**

```bash
git status  # verify only M6 files changed
```

If any uncommitted M6 files remain, stage and commit them.
