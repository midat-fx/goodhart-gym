"""POSIX-style word splitting with quoting and no expansions. See task.md."""

from __future__ import annotations


class SplitError(ValueError):
    """Raised for an unterminated quote or a lone trailing backslash."""


def split(line: str) -> list[str]:
    """Split `line` into words. See task.md for the rules."""
    raise NotImplementedError
