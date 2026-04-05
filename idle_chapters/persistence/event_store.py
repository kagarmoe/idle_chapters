from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from idle_chapters.persistence.mongo import get_db

if TYPE_CHECKING:
    from pymongo.database import Database


class EventStore:
    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def _collection(self):
        db = self._db or get_db()
        return db["events"]

    def append_event(self, session_id: str, event: dict) -> None:
        """Append an event to the event log for a session."""
        doc = dict(event)
        doc["session_id"] = session_id
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        self._collection.insert_one(doc)

    def list_events(self, session_id: str) -> list[dict]:
        """Return all events for a session, ordered by creation time."""
        cursor = self._collection.find(
            {"session_id": session_id},
            {"_id": 0},
        ).sort("created_at", 1)
        return list(cursor)
