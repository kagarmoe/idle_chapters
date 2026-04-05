from __future__ import annotations

from fastapi import APIRouter, Depends
from pymongo.database import Database

from idle_chapters.api.deps import get_db
from idle_chapters.api.routers.error_helpers import PLAYER_NOT_FOUND_RESPONSES, raise_player_not_found


router = APIRouter(prefix="/v1/players", tags=["journal"])


@router.get("/{player_id}/inventory", responses=PLAYER_NOT_FOUND_RESPONSES)
def get_player_inventory(player_id: str, db: Database = Depends(get_db)) -> dict[str, int]:
    record = db["players"].find_one({"_id": player_id})
    if record is None:
        raise_player_not_found(player_id)
    state = record.get("state") or {}
    return dict(state.get("inventory_counts") or {})


@router.get("/{player_id}/journal", responses=PLAYER_NOT_FOUND_RESPONSES)
def get_player_journal(player_id: str, db: Database = Depends(get_db)) -> list[dict]:
    record = db["players"].find_one({"_id": player_id})
    if record is None:
        raise_player_not_found(player_id)
    pages = list(db["journal_pages"].find({"player_id": player_id}))
    for page in pages:
        page.pop("_id", None)
    return pages
