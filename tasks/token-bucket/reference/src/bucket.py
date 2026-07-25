"""Per-key token bucket replayed over a timeline of events. See task.md."""

from __future__ import annotations

import math
from fractions import Fraction
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


def _config(config: dict) -> tuple[int, Fraction, int]:
    """Return (capacity, rate in tokens per ms, initial tokens)."""
    for name in ("capacity", "refill_tokens", "refill_interval_ms"):
        if name not in config:
            raise ConfigError(f"missing config key {name!r}")

    capacity = config["capacity"]
    refill_tokens = config["refill_tokens"]
    interval = config["refill_interval_ms"]
    if capacity < 1:
        raise ConfigError(f"capacity must be at least 1, got {capacity}")
    if refill_tokens < 1:
        raise ConfigError(f"refill_tokens must be at least 1, got {refill_tokens}")
    if interval < 1:
        raise ConfigError(f"refill_interval_ms must be at least 1, got {interval}")

    initial = config.get("initial_tokens", capacity)
    if not 0 <= initial <= capacity:
        raise ConfigError(f"initial_tokens must be within 0..{capacity}, got {initial}")

    return capacity, Fraction(refill_tokens, interval), initial


def _check_events(events: list[Event]) -> None:
    previous = None
    for event in events:
        timestamp, _key, cost = event
        if cost < 0:
            raise ConfigError(f"negative cost {cost}")
        if previous is not None and timestamp < previous:
            raise ConfigError(f"timestamp {timestamp} precedes {previous}")
        previous = timestamp


def decide(config: dict, events: list[Event]) -> list[Decision]:
    """Replay `events` through a per-key token bucket, one Decision each."""
    capacity, rate, initial = _config(config)
    _check_events(events)

    ceiling = Fraction(capacity)
    buckets: dict[str, tuple[int, Fraction]] = {}
    out: list[Decision] = []

    # Bounded by construction: one pass, one decision per event.
    for timestamp, key, cost in events:
        state = buckets.get(key)
        if state is None:
            tokens = Fraction(initial)
        else:
            last, tokens = state
            tokens = min(ceiling, tokens + (timestamp - last) * rate)

        if cost > capacity:
            # More than the bucket can ever hold: no wait would help.
            out.append(Decision(False, math.floor(tokens), -1))
        elif tokens >= cost:
            tokens -= cost
            out.append(Decision(True, math.floor(tokens), 0))
        else:
            # Smallest whole ms at which `cost` tokens have accrued. A denied
            # request takes nothing, so `tokens` is carried forward untouched.
            wait = math.ceil((cost - tokens) / rate)
            out.append(Decision(False, math.floor(tokens), wait))

        buckets[key] = (timestamp, tokens)

    return out
