from __future__ import annotations

from pymongo.database import Database

from idle_chapters.api.db import get_db as _get_db
from idle_chapters.domain.engine import Engine
from idle_chapters.services.session_service import SessionService


_CONTENT_REPO = None
_ENGINE = Engine()


def get_content_repo():
    global _CONTENT_REPO
    if _CONTENT_REPO is None:
        from idle_chapters.content.repo import ContentRepo

        _CONTENT_REPO = ContentRepo()
    return _CONTENT_REPO


def get_db() -> Database:
    return _get_db()


def get_session_service() -> SessionService:
    from idle_chapters.persistence.event_store import EventStore
    from idle_chapters.persistence.journal_store import JournalStore
    from idle_chapters.persistence.state_store import StateStore

    return SessionService(
        repo=get_content_repo(),
        engine=_ENGINE,
        state_store=StateStore(),
        journal_store=JournalStore(),
        event_store=EventStore(),
    )
