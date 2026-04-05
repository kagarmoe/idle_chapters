# M6: FastAPI v1 — Design

## Context

M0-M4 are complete (content loading, scenes, journal, domain engine). M5 adds persistence stores. M6 wires the FastAPI endpoints to the domain engine through a `SessionService`, making the game playable via HTTP.

A FastAPI shell already exists (`app/api/`) with routers, models, and Mongo access — but the sessions router is completely disconnected from `Engine.step()`. It does its own naive action matching. M6 replaces that with proper engine integration.

## Design Decisions

1. **Session service bridge** — `SessionService` class between routers and engine. Plain Python, no FastAPI imports. Reusable by CLI (M7).
2. **Keep /action, /enter, /intent** — User-friendly endpoints instead of a single `/step` with engine jargon.
3. **Imports from M5** — Uses `StateStore`, `JournalStore`, `EventStore` directly. No inline DB calls.
4. **Rewrite test_api.py** — Existing tests are entirely broken. Fresh tests against actual endpoints.

## Contracts

### M5 → M6 Contract

M6 imports these from `app/persistence/`:

```python
from idle_chapters.persistence.state_store import StateStore
# StateStore().upsert_state(session_id, state: PlayerState) -> None
# StateStore().get_state(session_id) -> PlayerState | None

from idle_chapters.persistence.journal_store import JournalStore
# JournalStore().append_page(session_id, page: dict) -> None
# JournalStore().list_pages(session_id) -> list[dict]
# JournalStore().get_page(session_id, page_id) -> dict | None

from idle_chapters.persistence.event_store import EventStore
# EventStore().append_event(session_id, event: dict) -> None
# EventStore().list_events(session_id) -> list[dict]
```

Field mapping (domain ↔ schema) is M5's responsibility. M6 passes and receives domain `PlayerState` objects.

### M6 → M7 Contract

M7 (CLI) can use either path:

**Direct import** (no HTTP):
```python
from idle_chapters.services.session_service import SessionService
service = SessionService(repo, state_store, journal_store, event_store)
session_id, result = service.create_session()
result = service.perform_action(session_id, "look_around")
```

**HTTP client** against endpoints:
```
POST /v1/sessions              -> {session_id, view, journal_page}
GET  /v1/sessions/{id}         -> {session_id, view, state}
POST /v1/sessions/{id}/enter   -> {view, journal_page, choices}
POST /v1/sessions/{id}/action  -> {view, journal_page, choices}
POST /v1/sessions/{id}/intent  -> {view, journal_page, choices}
GET  /v1/sessions/{id}/journal -> [{page}, ...]
```

## Architecture

### SessionService (`app/services/session_service.py`)

```python
class SessionService:
    def __init__(self, repo, state_store, journal_store, event_store): ...

    def create_session(self, place_id="cottage_home") -> tuple[str, StepResult]:
        # Generate session_id, create initial PlayerState
        # Engine.step("enter") for first scene
        # Persist state + journal page + event

    def enter(self, session_id) -> StepResult:
        # Load state, Engine.step("enter"), persist

    def perform_action(self, session_id, action_id) -> StepResult:
        # Load state, Engine.step("choose option", action_id), persist

    def submit_intent(self, session_id, text) -> StepResult:
        # Match text to eligible actions via intent_signature
        # Delegate to perform_action with matched action_id

    def get_session(self, session_id) -> PlayerState:
        # Load and return current state
```

### Sessions Router (`app/api/routers/sessions.py`) — rewrite

```
POST   /v1/sessions                      create_session
  Body: {place_id?: "cottage_home"}
  Returns: {session_id, view, journal_page}

GET    /v1/sessions/{session_id}         get_session
  Returns: {session_id, view, state}

POST   /v1/sessions/{session_id}/enter   enter_place
  Returns: {view, journal_page, choices}

POST   /v1/sessions/{session_id}/action  submit_action
  Body: {action_id: "look_around"}
  Returns: {view, journal_page, choices}

POST   /v1/sessions/{session_id}/intent  submit_intent
  Body: {input: "make some tea"}
  Returns: {view, journal_page, choices}
```

Router is thin — validates request, calls service, formats response. `SessionService` injected via `Depends`.

### Journal Endpoints (session-scoped)

Add to sessions router or a new sub-router:

```
GET /v1/sessions/{session_id}/journal            list journal pages
GET /v1/sessions/{session_id}/journal/{page_id}  get single page
```

Calls `JournalStore` directly. Existing player-scoped journal endpoints stay untouched.

### Response Models (`app/api/models.py`)

Update/add:

```python
class StepResponse:
    view: ViewModel            # scene prompt + eligible choices
    journal_page: dict | None  # rendered journal page
    choices: list[ViewAction]  # next available choices

class SessionCreateResponse:
    session_id: str
    view: ViewModel
    journal_page: dict | None
```

Drop unused `state_delta`, `applied_actions` from current `StepResponse`.

### Tests — rewrite `tests/test_api.py`

- Create session returns session_id + journal_page
- Enter returns choices
- Action with valid action_id returns new journal_page + updated state
- Intent matching resolves to correct action
- Get session returns current state
- Session journal endpoints work
- Use `TestClient` with real `ContentRepo`, mocked persistence stores

## Acceptance Criteria

From V1 plan:
- Swagger shows playable endpoints
- POST /sessions then POST /action returns JournalPage + choices
- State persists across calls
