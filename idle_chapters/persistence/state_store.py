from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.persistence.mongo import get_db

if TYPE_CHECKING:
    from pymongo.database import Database

    from app.domain.state import PlayerState


class StateStore:
    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def _collection(self):
        db = self._db or get_db()
        return db["sessions"]

    def upsert_state(self, session_id: str, state: PlayerState) -> None:
        """Persist player state into the sessions collection.

        Maps domain field names to schema field names (schema wins).
        """
        doc = {
            "state": {
                "current_location": state.current_place_id,
                "inventory_counts": dict(state.inventory),
                "flags": sorted(state.flags),
                "time_tick": state.time_tick,
                "visit_counts": dict(state.visit_counts),
                "seen_interactions": dict(state.seen_interactions),
                "current_scene_id": state.current_scene_id,
                "current_node_id": state.current_node_id,
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._collection.update_one(
            {"session_id": session_id},
            {"$set": doc, "$setOnInsert": {"session_id": session_id, "created_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )

    def get_state(self, session_id: str) -> PlayerState | None:
        """Load player state from the sessions collection.

        Maps schema field names back to domain field names.
        Returns None if session not found.
        """
        from app.domain.state import PlayerState

        doc = self._collection.find_one({"session_id": session_id})
        if doc is None:
            return None

        s = doc.get("state", {})
        return PlayerState(
            session_id=session_id,
            current_place_id=s.get("current_location", ""),
            inventory=dict(s.get("inventory_counts") or {}),
            flags=set(s.get("flags") or []),
            time_tick=s.get("time_tick", 0),
            visit_counts=dict(s.get("visit_counts") or {}),
            seen_interactions=dict(s.get("seen_interactions") or {}),
            current_scene_id=s.get("current_scene_id"),
            current_node_id=s.get("current_node_id"),
        )
