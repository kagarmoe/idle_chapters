"""Soft time: the day drifts on as the player does things. No clock, nothing due."""

from __future__ import annotations

PHASES = ("morning", "midday", "afternoon", "dusk", "evening", "night")
TICKS_PER_PHASE = 3
TICKS_PER_DAY = TICKS_PER_PHASE * len(PHASES)


def time_of_day(time_tick: int) -> str:
    return PHASES[(time_tick // TICKS_PER_PHASE) % len(PHASES)]


def day(time_tick: int) -> int:
    return time_tick // TICKS_PER_DAY
