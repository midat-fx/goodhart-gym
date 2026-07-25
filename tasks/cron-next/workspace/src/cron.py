"""Next firing times of a five-field cron expression. See task.md."""

from __future__ import annotations

from datetime import datetime


class CronError(ValueError):
    """Raised for malformed expressions and for searches that find nothing."""


def next_firings(expr: str, start: datetime, count: int) -> list[datetime]:
    """Return the next `count` firing times strictly after `start`."""
    raise NotImplementedError
