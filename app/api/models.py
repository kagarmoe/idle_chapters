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
    player_id: str


class IntentRequest(BaseModel):
    input: str


class ActionRequest(BaseModel):
    action_id: str


class SessionResponse(BaseModel):
    session_id: str
    player_id: str
    view: ViewModel
    state_digest: str | None = None


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


class StepResponse(BaseModel):
    view: ViewModel
    applied_actions: list[str] = Field(default_factory=list)
    state_delta: dict[str, Any] = Field(default_factory=dict)
    journal_entries: list[dict[str, Any]] = Field(default_factory=list)
