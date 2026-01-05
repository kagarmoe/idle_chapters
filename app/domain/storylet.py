from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Storylet:
    storylet_id: str
    place_id: str
    entry_type: str
    choices: list[dict[str, Any]]
    title: str | None = None
    prompt: str | None = None
    tags: list[str] = field(default_factory=list)
    need_hint: str | None = None
    mood_hint: str | None = None
    conditions: dict[str, Any] = field(default_factory=dict)
    debug: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "storylet_id": self.storylet_id,
            "place_id": self.place_id,
            "entry_type": self.entry_type,
            "title": self.title,
            "prompt": self.prompt,
            "tags": list(self.tags),
            "need_hint": self.need_hint,
            "mood_hint": self.mood_hint,
            "conditions": dict(self.conditions),
            "choices": list(self.choices),
            "debug": dict(self.debug) if self.debug is not None else None,
        }
