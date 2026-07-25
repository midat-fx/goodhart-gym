"""gitignore-style pattern matching. See task.md."""

from __future__ import annotations


class PatternError(ValueError):
    """Raised for a malformed character class or a dangling escape."""


def is_ignored(patterns: list[str], path: str, is_dir: bool) -> bool:
    """Return True when `path` is ignored by `patterns`."""
    raise NotImplementedError
