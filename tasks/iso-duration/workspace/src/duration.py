"""ISO-8601 durations: parsing, calendar addition and canonical output.

See task.md. `Duration` and `DurationError` are part of the contract: keep their
names, fields and field order as they are.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class DurationError(ValueError):
    """Raised for text that is not a well-formed ISO-8601 duration."""


@dataclass(frozen=True)
class Duration:
    """A duration. Every component is non-negative; `negative` signs the whole."""

    years: int = 0
    months: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    microseconds: int = 0
    negative: bool = False


def parse(text: str) -> Duration:
    """Parse an ISO-8601 duration."""
    raise NotImplementedError


def add(start: datetime, duration: Duration) -> datetime:
    """Return `start` shifted by `duration`, calendar-correct."""
    raise NotImplementedError


def format(duration: Duration) -> str:  # noqa: A001 - the contract names it this
    """Return the canonical ISO-8601 text for `duration`."""
    raise NotImplementedError
