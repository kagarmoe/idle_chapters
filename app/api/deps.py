from __future__ import annotations

from pymongo.database import Database

from app.api.db import get_db as _get_db
from app.content.repo import ContentRepo


CONTENT_REPO = ContentRepo()


def get_content_repo() -> ContentRepo:
    return CONTENT_REPO


def get_db() -> Database:
    return _get_db()
