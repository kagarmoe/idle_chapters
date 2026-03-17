from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.api.deps import get_db


router = APIRouter(prefix="/v1/players", tags=["journal"])


@router.get("/{player_id}/inventory")
def get_player_inventory(player_id: str, db: Database = Depends(get_db)) -> dict[str, int]:
    record = db["players"].find_one({"_id": player_id})
    if record is None:
        raise HTTPException(status_code=404, detail="Player not found")
    state = record.get("state") or {}
    return dict(state.get("inventory_counts") or {})


@router.get("/{player_id}/journal")
def get_player_journal(player_id: str, db: Database = Depends(get_db)) -> list[dict]:
    record = db["players"].find_one({"_id": player_id})
    if record is None:
        raise HTTPException(status_code=404, detail="Player not found")
    pages = list(db["journal_pages"].find({"player_id": player_id}))
    for page in pages:
        page.pop("_id", None)
    return pages
