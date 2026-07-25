"""Changelog and version files from Conventional Commit messages. See task.md."""

from __future__ import annotations


class CommitError(ValueError):
    """Raised when `previous_version` is not a valid `X.Y.Z` version."""


def build(commits: list[str], previous_version: str, out_dir: str) -> None:
    """Write `<out_dir>/CHANGELOG.md` and `<out_dir>/version.txt`."""
    raise NotImplementedError
