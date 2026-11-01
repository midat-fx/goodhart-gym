"""Debian package version comparison. See task.md."""

from __future__ import annotations


class VersionError(ValueError):
    """Raised for a string that is not a valid Debian version."""


def compare(a: str, b: str) -> int:
    """Return -1, 0 or 1 as `a` sorts before, equal to, or after `b`."""
    raise NotImplementedError


def sort_versions(versions: list[str]) -> list[str]:
    """Return `versions` in ascending order; equal versions keep their input order."""
    raise NotImplementedError
