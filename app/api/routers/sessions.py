from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_session_service
from app.api.models import (
    ActionRequest,
    IntentRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionGetResponse,
    StepResponse,
    ViewAction,
    ViewModel,
)
from app.domain.step_result import StepResult
from app.services.session_service import SessionService

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
