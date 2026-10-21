from __future__ import annotations

import os

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database


_CLIENT: MongoClient | None = None


def get_db() -> Database:
    """Return the MongoDB database, creating the client on first call."""
    global _CLIENT
    db_name = os.getenv("MONGO_DB", "idle_chapters")
    if _CLIENT is None:
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        if mongo_url.startswith("memory://"):
            # shortcut: per-process memory, lost on restart; set a real MONGO_URL for durable saves.
            import mongomock

            client = mongomock.MongoClient()
        else:
            client = MongoClient(mongo_url)
        # Every step counts and lists a session's pages; idempotent, so cold starts are safe.
        client[db_name].journal_pages.create_index([("session_id", ASCENDING), ("created_at", ASCENDING)])
        _CLIENT = client
    return _CLIENT[db_name]
