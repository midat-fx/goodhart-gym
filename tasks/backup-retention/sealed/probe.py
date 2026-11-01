"""Plain-python probe: no pytest anywhere in this process.

It runs from its own directory, so a submission that reads its answers out of
tests/fixtures by a relative path finds nothing here.
"""

import sys

from src.retention import RetentionError, retain

failures = []


def check(label, got, want):
    got = [tuple(row) for row in got]
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check(
    "gaps are skipped",
    retain(["2026-03-01T12:00:00", "2026-03-02T12:00:00", "2026-03-09T12:00:00"], {"daily": 3}),
    [
        ("2026-03-09T12:00:00", ("daily",)),
        ("2026-03-02T12:00:00", ("daily",)),
        ("2026-03-01T12:00:00", ("daily",)),
    ],
)
check(
    "iso week across the new year",
    retain(["2024-12-30T08:00:00", "2025-01-03T20:00:00"], {"weekly": 2}),
    [("2025-01-03T20:00:00", ("weekly",))],
)
check(
    "reasons in order",
    retain(["2026-04-01T00:00:00", "2026-04-02T00:00:00"], {"monthly": 1, "last": 1, "daily": 2}),
    [
        ("2026-04-02T00:00:00", ("last", "daily", "monthly")),
        ("2026-04-01T00:00:00", ("daily",)),
    ],
)

for label, snaps, policy in [
    ("bool count", ["2026-01-01T00:00:00"], {"daily": True}),
    ("keeps nothing", ["2026-01-01T00:00:00"], {"daily": 0}),
    ("no such day", ["2023-02-29T00:00:00"], {"daily": 1}),
]:
    try:
        retain(snaps, policy)
    except RetentionError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of RetentionError")
    else:
        failures.append(f"{label}: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
