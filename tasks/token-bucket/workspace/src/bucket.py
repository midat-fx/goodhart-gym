"""Per-key token bucket replayed over a timeline of events. See task.md."""

from __future__ import annotations

from typing import NamedTuple


class ConfigError(ValueError):
    """Raised for an unusable config and for an unusable event stream."""


class Event(NamedTuple):
    timestamp_ms: int
    key: str
    cost: int


class Decision(NamedTuple):
    allowed: bool
    remaining: int
    retry_after_ms: int


def decide(config: dict, events: list[Event]) -> list[Decision]:
    """Replay `events` through a per-key token bucket, one Decision each."""
    raise NotImplementedError
