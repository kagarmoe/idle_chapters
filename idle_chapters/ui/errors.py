"""CLI projection of GameError: player templates + optional Z535 detail.

Default output is purely tone-contract (the player message). Verbose mode
prepends the Z535 signal word on stdout and writes the WHAT/MEANS/DO
three-panel detail to stderr.
"""

from __future__ import annotations

import sys

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.ui.text import print_block, wrap_text

# ponytail: module-level flag, not threaded through scene signatures;
# revisit if the CLI ever grows per-command verbosity.
_verbose = False


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = value


def is_verbose() -> bool:
    return _verbose


def invalid_choice(selection: str, labels: list[str]) -> GameError:
    """A menu input that matched nothing the scene offered."""
    return GameError(
        kind=ErrorKind.INTENT_NO_MATCH,
        effect=Effect.NONE,
        recovery=Recovery.CORRECTABLE,
        context={"input": selection, "available_actions": ", ".join(labels)},
    )


def print_error(err: GameError) -> None:
    """Render a GameError for the terminal (the CLI projection)."""
    if not _verbose:
        print_block(err.player_message)
        return
    print_block(f"{err.signal.value}: {err.player_message}")
    if err.detail:
        for panel in err.detail.splitlines():
            print(wrap_text(panel), file=sys.stderr)
