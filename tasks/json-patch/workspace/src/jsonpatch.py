"""Apply a JSON Patch (RFC 6902) to a JSON document. See task.md."""

from __future__ import annotations

from typing import Any


class PatchError(ValueError):
    """Raised when a patch is malformed or cannot be applied."""


def apply(document: Any, patch: list[dict]) -> Any:
    """Return the result of applying `patch` to `document`."""
    raise NotImplementedError
