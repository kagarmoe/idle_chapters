from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.api.deps import get_db
from app.api.models import PlayerCreateRequest, PlayerResponse, PlayerState, PlayerUpdateRequest


router = APIRouter(prefix="/v1/players", tags=["players"])


def _build_player_response(player_id: str, record: dict) -> PlayerResponse:
    return PlayerResponse(
        player_id=player_id,
        address=record.get("address"),
        state=record.get("state"),
    )


@router.post("", response_model=PlayerResponse)
def create_player(
    request: PlayerCreateRequest, db: Database = Depends(get_db)
) -> PlayerResponse:
    player_id = uuid4().hex
    address = {
        "display_name": request.display_name,
        "pronouns": request.pronouns_key or "unspecified",
    }
    state = PlayerState().model_dump()
    db["players"].insert_one({"_id": player_id, "address": address, "state": state})
    return _build_player_response(player_id, {"address": address, "state": state})


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: str, db: Database = Depends(get_db)) -> PlayerResponse:
    record = db["players"].find_one({"_id": player_id})
    if record is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return _build_player_response(player_id, record)


@router.patch("/{player_id}", response_model=PlayerResponse)
def update_player(
    player_id: str, request: PlayerUpdateRequest, db: Database = Depends(get_db)
) -> PlayerResponse:
    record = db["players"].find_one({"_id": player_id})
    if record is None:
        raise HTTPException(status_code=404, detail="Player not found")
    address = dict(record.get("address") or {})
    if request.display_name is not None:
        address["display_name"] = request.display_name
    if request.pronouns_key is not None:
        address["pronouns"] = request.pronouns_key
    db["players"].update_one({"_id": player_id}, {"$set": {"address": address}})
    record["address"] = address
    return _build_player_response(player_id, record)
