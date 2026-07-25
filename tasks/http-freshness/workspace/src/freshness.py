"""Freshness of a stored HTTP response, an RFC 9111 subset. See task.md."""

from __future__ import annotations

from dataclasses import dataclass

FRESH = "FRESH"
STALE = "STALE"
MUST_REVALIDATE = "MUST_REVALIDATE"


class HeaderError(ValueError):
    """Raised for a header that is not a well-formed HTTP-date."""


@dataclass(frozen=True)
class Result:
    verdict: str
    current_age: int
    freshness_lifetime: int


def evaluate(
    response_headers: dict[str, str],
    request_headers: dict[str, str],
    request_time: int,
    response_time: int,
    now: int,
) -> Result:
    """Decide whether the stored response may be reused at `now`."""
    raise NotImplementedError
