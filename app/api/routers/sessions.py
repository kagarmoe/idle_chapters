from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.api.deps import get_content_repo, get_db
from app.api.models import (
    ActionRequest,
    IntentRequest,
    SessionCreateRequest,
    SessionResponse,
    StepResponse,
    ViewAction,
    ViewModel,
)
from app.content.repo import ContentRepo


router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


def _find_scene(repo: ContentRepo, scene_id: str) -> dict:
    scene = repo.scenes_by_id.get(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


def _find_node(scene: dict, node_id: str) -> dict:
    for node in scene.get("nodes", []):
        if node.get("node_id") == node_id:
            return node
    raise HTTPException(status_code=404, detail="Scene node not found")


def _action_for_node(repo: ContentRepo, node: dict) -> dict | None:
    action_id = node.get("action_ref")
    if not action_id:
        return None
    return repo.actions_by_id.get(str(action_id))


def _build_view(repo: ContentRepo, scene: dict, node: dict) -> ViewModel:
    action = _action_for_node(repo, node) or {}
    prompt = action.get("result") or action.get("label")
    choices = node.get("choices", [])
    eligible_actions = []
    for choice_id in choices:
        choice_action = repo.actions_by_id.get(str(choice_id))
        if choice_action:
            eligible_actions.append(
                ViewAction(action_id=choice_action["action_id"], label=choice_action["label"])
            )
    return ViewModel(
        prompt=prompt,
        scene_id=scene.get("scene_id"),
        eligible_actions=eligible_actions,
        visible_items=[],
        visible_npcs=[],
    )


def _select_start_scene(repo: ContentRepo, player_state: dict | None) -> dict:
    if player_state:
        current_location = player_state.get("current_location")
        if current_location:
            scenes = repo.scenes_by_place_id.get(str(current_location))
            if scenes:
                return scenes[0]
    if repo.scenes_by_id:
        return next(iter(repo.scenes_by_id.values()))
    raise HTTPException(status_code=404, detail="No scenes available")


def _match_intent_action(input_text: str, node: dict, repo: ContentRepo) -> str | None:
    text = input_text.lower()
    for choice_id in node.get("choices", []):
        action = repo.actions_by_id.get(str(choice_id))
        if not action:
            continue
        label = str(action.get("label", "")).lower()
        if label and label in text:
            return action["action_id"]
        signature = action.get("intent_signature") or {}
        for phrase in signature.get("phrases", []):
            if str(phrase).lower() in text:
                return action["action_id"]
        for keyword in signature.get("keywords", []):
            if str(keyword).lower() in text:
                return action["action_id"]
    return None


def _apply_action(session: dict, action_id: str, repo: ContentRepo, db: Database) -> StepResponse:
    scene = _find_scene(repo, session["scene_id"])
    current_node = _find_node(scene, session["node_id"])
    choices = current_node.get("choices", [])
    target_node = None
    for node in scene.get("nodes", []):
        if node.get("node_id") == action_id or node.get("action_ref") == action_id:
            target_node = node
            break
    if target_node is None or action_id not in choices:
        raise HTTPException(status_code=400, detail="Action not eligible")

    session["node_id"] = target_node.get("node_id")
    db["sessions"].update_one(
        {"_id": session["_id"]},
        {"$set": {"node_id": session["node_id"]}},
    )
    view = _build_view(repo, scene, target_node)
    return StepResponse(view=view, applied_actions=[action_id], state_delta={}, journal_entries=[])


@router.post("", response_model=SessionResponse)
def create_session(
    request: SessionCreateRequest,
    repo: ContentRepo = Depends(get_content_repo),
    db: Database = Depends(get_db),
) -> SessionResponse:
    player = db["players"].find_one({"_id": request.player_id})
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    scene = _select_start_scene(repo, player.get("state"))
    node_id = scene.get("entry_node")
    if node_id is None:
        raise HTTPException(status_code=500, detail="Scene has no entry node")

    session_id = uuid4().hex
    db["sessions"].insert_one(
        {
            "_id": session_id,
            "player_id": request.player_id,
            "scene_id": scene.get("scene_id"),
            "node_id": node_id,
        }
    )
    node = _find_node(scene, node_id)
    view = _build_view(repo, scene, node)
    return SessionResponse(session_id=session_id, player_id=request.player_id, view=view)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    repo: ContentRepo = Depends(get_content_repo),
    db: Database = Depends(get_db),
) -> SessionResponse:
    session = db["sessions"].find_one({"_id": session_id})
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    scene = _find_scene(repo, session["scene_id"])
    node = _find_node(scene, session["node_id"])
    view = _build_view(repo, scene, node)
    return SessionResponse(
        session_id=session_id,
        player_id=session["player_id"],
        view=view,
        state_digest=None,
    )


@router.post("/{session_id}/intent", response_model=StepResponse)
def submit_intent(
    session_id: str,
    request: IntentRequest,
    repo: ContentRepo = Depends(get_content_repo),
    db: Database = Depends(get_db),
) -> StepResponse:
    session = db["sessions"].find_one({"_id": session_id})
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    scene = _find_scene(repo, session["scene_id"])
    node = _find_node(scene, session["node_id"])
    action_id = _match_intent_action(request.input, node, repo)
    if action_id is None:
        raise HTTPException(status_code=400, detail="No eligible action matched")
    return _apply_action(session, action_id, repo, db)


@router.post("/{session_id}/action", response_model=StepResponse)
def submit_action(
    session_id: str,
    request: ActionRequest,
    repo: ContentRepo = Depends(get_content_repo),
    db: Database = Depends(get_db),
) -> StepResponse:
    session = db["sessions"].find_one({"_id": session_id})
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _apply_action(session, request.action_id, repo, db)


@router.post("/{session_id}/peek", response_model=StepResponse)
def peek_session(
    session_id: str,
    repo: ContentRepo = Depends(get_content_repo),
    db: Database = Depends(get_db),
) -> StepResponse:
    session = db["sessions"].find_one({"_id": session_id})
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    scene = _find_scene(repo, session["scene_id"])
    node = _find_node(scene, session["node_id"])
    view = _build_view(repo, scene, node)
    return StepResponse(view=view, applied_actions=[], state_delta={}, journal_entries=[])
