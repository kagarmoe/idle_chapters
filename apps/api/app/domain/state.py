from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlayerState:
    session_id: str
    current_place_id: str
    inventory: dict[str, int]
    flags: set[str]
    time_tick: int = 0
    visit_counts: dict[str, int] = field(default_factory=dict)
    seen_interactions: dict[str, int] = field(default_factory=dict)
    current_scene_id: str | None = None
    current_node_id: str | None = None
