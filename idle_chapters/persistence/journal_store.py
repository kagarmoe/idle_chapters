from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from idle_chapters.persistence.mongo import get_db

if TYPE_CHECKING:
    from pymongo.database import Database


class JournalStore:
    def __init__(self, db: Database | None = None):
        self._db = db

    @property
    def _collection(self):
        db = self._db or get_db()
        return db["journal_pages"]

    def append_page(self, session_id: str, page: dict) -> None:
        """Append a journal page for the given session."""
        doc = dict(page)
        doc["session_id"] = session_id
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        self._collection.insert_one(doc)

    def list_pages(self, session_id: str) -> list[dict]:
        """Return all journal pages for a session, ordered by creation time."""
        cursor = self._collection.find(
            {"session_id": session_id},
            {"_id": 0},
        ).sort("created_at", 1)
        return list(cursor)

    def get_page(self, session_id: str, page_id: str) -> dict | None:
        """Return a single journal page by page_id within a session."""
        doc = self._collection.find_one(
            {"session_id": session_id, "page_id": page_id},
            {"_id": 0},
        )
        return doc
