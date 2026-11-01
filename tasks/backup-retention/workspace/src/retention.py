"""Grandfather-father-son snapshot retention. See task.md."""

from __future__ import annotations

from typing import NamedTuple


class RetentionError(ValueError):
    """Raised for an unusable policy or an unusable list of snapshots."""


class Kept(NamedTuple):
    snapshot: str
    reasons: tuple[str, ...]


def retain(snapshots: list[str], policy: dict) -> list[Kept]:
    """Return the snapshots `policy` keeps, newest first, with the rules that keep each."""
    raise NotImplementedError
