"""Grandfather-father-son snapshot retention. See task.md."""

from __future__ import annotations

import re
from datetime import datetime
from typing import NamedTuple


class RetentionError(ValueError):
    """Raised for an unusable policy or an unusable list of snapshots."""


class Kept(NamedTuple):
    snapshot: str
    reasons: tuple[str, ...]


TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")

# Rule name -> the bucket a snapshot falls in. `last` puts every snapshot in a
# bucket of its own, which makes it the same walk as the calendar rules.
BUCKETS = {
    "last": lambda t: t,
    "hourly": lambda t: (t.date(), t.hour),
    "daily": lambda t: t.date(),
    "weekly": lambda t: t.isocalendar()[:2],
    "monthly": lambda t: (t.year, t.month),
    "yearly": lambda t: t.year,
}


def _policy(policy: dict) -> dict[str, int]:
    unknown = set(policy) - set(BUCKETS)
    if unknown:
        raise RetentionError(f"unknown policy keys: {sorted(map(str, unknown))}")
    for key, value in policy.items():
        # bool is a subclass of int, and must not pass for one here.
        if type(value) is not int or value < 0:
            raise RetentionError(f"{key} must be a non-negative int, got {value!r}")
    if not any(policy.values()):
        raise RetentionError("the policy keeps nothing")
    return {key: policy.get(key, 0) for key in BUCKETS}


def _parse(snapshot: str) -> datetime:
    if not isinstance(snapshot, str) or not TIMESTAMP.fullmatch(snapshot):
        raise RetentionError(f"not a timestamp: {snapshot!r}")
    try:
        return datetime.strptime(snapshot, "%Y-%m-%dT%H:%M:%S")
    except ValueError as exc:
        raise RetentionError(f"no such time: {snapshot!r}") from exc


def retain(snapshots: list[str], policy: dict) -> list[Kept]:
    """Return the snapshots `policy` keeps, newest first, with the rules that keep each."""
    counts = _policy(policy)
    parsed = {}
    for snapshot in snapshots:
        moment = _parse(snapshot)
        if snapshot in parsed:
            raise RetentionError(f"duplicate snapshot {snapshot!r}")
        parsed[snapshot] = moment

    newest_first = sorted(parsed, key=parsed.__getitem__, reverse=True)
    reasons: dict[str, list[str]] = {s: [] for s in newest_first}

    for rule, bucket_of in BUCKETS.items():
        seen = set()
        for snapshot in newest_first:
            if len(seen) >= counts[rule]:
                break
            bucket = bucket_of(parsed[snapshot])
            if bucket not in seen:
                seen.add(bucket)
                reasons[snapshot].append(rule)

    return [Kept(s, tuple(r)) for s, r in reasons.items() if r]
