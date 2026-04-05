from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ViewAction(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "action_id": "rest_longer",
        "label": "Rest a bit longer",
    }})

    action_id: str
    label: str


class ViewModel(BaseModel):
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

    session_id: str
    view: ViewModel
    journal_page: dict | None = None


class SessionGetResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "session_id": "a1b2c3d4e5f67890abcdef1234567890",
        "view": {
            "prompt": "(no active scene)",
            "scene_id": "",
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

    session_id: str
    view: ViewModel
    state: dict | None = None


class StepResponse(BaseModel):
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
    model_config = ConfigDict(json_schema_extra={"example": {
        "player_id": "f1e2d3c4b5a67890abcdef1234567890",
        "player_info": {
            "display_name": "Wanderer",
            "pronouns": "they/them",
        },
        "state": {
            "inventory_counts": {},
            "visit_counts": {},
            "seen_interactions": {},
            "flags": [],
        },
    }})

    player_id: str
    player_info: PlayerInfo | None = None
    state: PlayerState | None = None


class ProblemDetailPlayer(BaseModel):
    """Minimal RFC 9457 response for player projection."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "type": "urn:idle-chapters:error:session_not_found",
        "title": "That story has found its own ending. You're welcome to begin a new one whenever you'd like.",
        "status": 404,
    }})

    type: str
    title: str
    status: int


class ProblemDetailDeveloper(BaseModel):
    """Full RFC 9457 response with Z535 extensions for developer projection."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "type": "urn:idle-chapters:error:session_not_found",
        "title": "Session Not Found",
        "status": 404,
        "detail": "WHAT: No session exists for abc123.\nMEANS: Nothing was modified.\nDO: Create a new session via POST /v1/sessions.",
        "instance": "urn:idle-chapters:occurrence:a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "effect": "none",
        "recovery": "terminal",
        "signal": "NOTICE",
        "context": {"session_id": "abc123"},
    }})

    type: str
    title: str
    status: int
    detail: str
    instance: str
    effect: str
    recovery: str
    signal: str
    context: dict[str, Any] = Field(default_factory=dict)
