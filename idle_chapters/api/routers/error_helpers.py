"""Shared error helpers for API routers."""
from __future__ import annotations

from typing import NoReturn

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery


def raise_player_not_found(player_id: str) -> NoReturn:
    """Raise a GameError for a missing player."""
    raise GameError(
        kind=ErrorKind.PLAYER_NOT_FOUND,
        effect=Effect.NONE,
        recovery=Recovery.TERMINAL,
        detail=(
            f"WHAT: No player exists for {player_id}.\n"
            f"MEANS: Nothing was modified.\n"
            f"DO: Create a new player via POST /v1/players."
        ),
        context={"player_id": player_id},
    )
