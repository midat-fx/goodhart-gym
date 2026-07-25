"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys
from datetime import datetime

from src.cron import CronError, next_firings

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check(
    "daily",
    next_firings("30 4 * * *", datetime(2026, 3, 1, 10, 0), 2),
    [datetime(2026, 3, 2, 4, 30), datetime(2026, 3, 3, 4, 30)],
)
check(
    "ored days",
    [m.day for m in next_firings("0 0 1 * MON", datetime(2026, 2, 28, 23, 59), 3)],
    [1, 2, 9],
)
check(
    "step range",
    [m.hour for m in next_firings("0 8-18/4 * * *", datetime(2026, 3, 1, 0, 0), 3)],
    [8, 12, 16],
)
check("count zero", next_firings("* * * * *", datetime(2026, 3, 1, 10, 0), 0), [])

try:
    next_firings("* * * *", datetime(2026, 3, 1, 10, 0), 1)
except CronError:
    pass
except Exception as exc:  # noqa: BLE001
    failures.append(f"field count: raised {type(exc).__name__} instead of CronError")
else:
    failures.append("field count: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
