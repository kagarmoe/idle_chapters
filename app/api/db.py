from __future__ import annotations

import os

from pymongo import MongoClient
from pymongo.database import Database


_CLIENT: MongoClient | None = None


def get_db() -> Database:
    global _CLIENT
    if _CLIENT is None:
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        _CLIENT = MongoClient(mongo_url)
    db_name = os.getenv("MONGO_DB", "idle_chapters")
    return _CLIENT[db_name]
