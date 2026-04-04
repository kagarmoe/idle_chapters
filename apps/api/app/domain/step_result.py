from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.state import PlayerState


@dataclass
class StepResult:
    journal_page: dict | None
    choices: list[dict]
    new_state: PlayerState
    debug: dict | None = None
