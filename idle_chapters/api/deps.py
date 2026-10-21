from __future__ import annotations

from pymongo.database import Database

from idle_chapters.api.db import get_db as _get_db
from idle_chapters.domain.engine import Engine
from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.services.session_service import SessionService


_CONTENT_REPO = None
_ENGINE = Engine()


def get_content_repo():
    global _CONTENT_REPO
    if _CONTENT_REPO is None:
        from idle_chapters.content.repo import ContentRepo
        from idle_chapters.content.validators import validate_cross_file_integrity

        repo = ContentRepo()
        try:
            validate_cross_file_integrity(repo)
        except ValueError as exc:
            raise GameError(
                kind=ErrorKind.ENGINE_FAILURE,
                effect=Effect.NONE,
                recovery=Recovery.ESCALATE,
                detail=(
                    f"WHAT: Content failed cross-file integrity: {exc}\n"
                    f"MEANS: Nothing was modified; no request can be served until content is fixed.\n"
                    f"DO: Fix the dangling reference in assets/ and redeploy."
                ),
            ) from exc
        _CONTENT_REPO = repo
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
