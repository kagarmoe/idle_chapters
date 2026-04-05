from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends

from idle_chapters.api.deps import get_session_service
from idle_chapters.api.routers.error_helpers import (
    SESSION_NOT_FOUND_RESPONSES,
    ACTION_NOT_ELIGIBLE_RESPONSES,
    INTENT_NO_MATCH_RESPONSES,
    JOURNAL_PAGE_404_RESPONSES,
)
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
from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
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
            ViewAction(
                action_id=c.get("action_id") or c.get("choice_id", ""),
                label=c.get("label", c.get("action_id") or c.get("choice_id", "")),
            )
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


def _raise_session_not_found(session_id: str) -> NoReturn:
    """Raise a GameError for a missing session. Used by read-only endpoints."""
    raise GameError(
        kind=ErrorKind.SESSION_NOT_FOUND,
        effect=Effect.NONE,
        recovery=Recovery.TERMINAL,
        detail=(
            f"WHAT: No session exists for {session_id}.\n"
            f"MEANS: Nothing was modified.\n"
            f"DO: Create a new session via POST /v1/sessions."
        ),
        context={"session_id": session_id},
    )


@router.post(
    "",
    response_model=SessionCreateResponse,
    description="""Create a new game session and enter the starting location.

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
""",
)
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


@router.get(
    "/{session_id}",
    response_model=SessionGetResponse,
    responses=SESSION_NOT_FOUND_RESPONSES,
    description="""Get the current state of a game session.

**curl:**
```bash
curl http://localhost:8000/v1/sessions/{session_id}
```
""",
)
def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> SessionGetResponse:
    state = service.get_session(session_id)
    if state is None:
        _raise_session_not_found(session_id)
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


@router.post(
    "/{session_id}/enter",
    response_model=StepResponse,
    responses=SESSION_NOT_FOUND_RESPONSES,
)
def enter_place(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    result = service.enter(session_id)
    return _step_response(result)


@router.post(
    "/{session_id}/action",
    response_model=StepResponse,
    responses={**SESSION_NOT_FOUND_RESPONSES, **ACTION_NOT_ELIGIBLE_RESPONSES},
    description="""Execute a chosen action in the current scene.

**curl:**
```bash
curl -X POST http://localhost:8000/v1/sessions/{session_id}/action \\
  -H "Content-Type: application/json" \\
  -d '{"action_id": "rest_longer"}'
```

To see developer error details, add the projection header:
```bash
curl -H "Accept-Projection: developer" http://localhost:8000/v1/sessions/{session_id}/action ...
```
""",
)
def submit_action(
    session_id: str,
    request: ActionRequest,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    result = service.perform_action(session_id, request.action_id)
    return _step_response(result)


@router.post(
    "/{session_id}/intent",
    response_model=StepResponse,
    responses={**SESSION_NOT_FOUND_RESPONSES, **INTENT_NO_MATCH_RESPONSES},
)
def submit_intent(
    session_id: str,
    request: IntentRequest,
    service: SessionService = Depends(get_session_service),
) -> StepResponse:
    result = service.submit_intent(session_id, request.input)
    return _step_response(result)


@router.get(
    "/{session_id}/journal",
    responses=SESSION_NOT_FOUND_RESPONSES,
)
def list_journal_pages(
    session_id: str,
    service: SessionService = Depends(get_session_service),
) -> list[dict]:
    state = service.get_session(session_id)
    if state is None:
        _raise_session_not_found(session_id)
    return service._journal_store.list_pages(session_id)


@router.get(
    "/{session_id}/journal/{page_id}",
    responses=JOURNAL_PAGE_404_RESPONSES,
)
def get_journal_page(
    session_id: str,
    page_id: str,
    service: SessionService = Depends(get_session_service),
) -> dict:
    state = service.get_session(session_id)
    if state is None:
        _raise_session_not_found(session_id)
    page = service._journal_store.get_page(session_id, page_id)
    if page is None:
        raise GameError(
            kind=ErrorKind.JOURNAL_PAGE_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            detail=(
                f"WHAT: Journal page {page_id} not found for session {session_id}.\n"
                f"MEANS: Nothing was modified.\n"
                f"DO: List pages via GET /v1/sessions/{session_id}/journal."
            ),
            context={"session_id": session_id, "page_id": page_id},
        )
    return page
