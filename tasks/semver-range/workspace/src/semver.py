"""Highest version in a list satisfying an npm-style range. See task.md."""

from __future__ import annotations


class RangeError(ValueError):
    """Raised for malformed range expressions and malformed versions."""


def max_satisfying(versions: list[str], range_expr: str) -> str | None:
    """Return the highest version in `versions` that satisfies `range_expr`."""
    raise NotImplementedError
