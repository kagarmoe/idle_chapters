from __future__ import annotations

from pymongo.database import Database

from app.api.db import get_db as _get_db
from app.content.repo import ContentRepo
from app.domain.engine import Engine
from app.services.session_service import SessionService


CONTENT_REPO = ContentRepo()

_ENGINE = Engine()


def get_content_repo() -> ContentRepo:
    return CONTENT_REPO


def get_db() -> Database:
    return _get_db()


def get_session_service() -> SessionService:
    from app.persistence.event_store import EventStore
    from app.persistence.journal_store import JournalStore
    from app.persistence.state_store import StateStore

    return SessionService(
        repo=CONTENT_REPO,
        engine=_ENGINE,
        state_store=StateStore(),
        journal_store=JournalStore(),
        event_store=EventStore(),
    )
