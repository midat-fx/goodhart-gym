"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here. The backoff chain below is long enough, and
uses a factor binary floating point cannot hold (7/5), that any implementation
routing through `float` truncates at least one delay to the wrong millisecond.
"""

import math
import sys
from fractions import Fraction

from src.retry import PolicyError, plan

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def retryable(count):
    return [{"status": 503} for _ in range(count)]


ATTEMPTS = 12
BASE = 1000
FACTOR = Fraction(7, 5)

# Derived here from the rule in task.md, not from any implementation.
want_delays = [0] + [
    math.floor(BASE * FACTOR ** (n - 2)) for n in range(2, ATTEMPTS + 1)
]
want_starts = []
running = 0
for delay in want_delays:
    running += delay
    want_starts.append(running)

chain = plan(
    {
        "base_ms": BASE,
        "factor": [7, 5],
        "max_delay_ms": 10**9,
        "max_attempts": ATTEMPTS,
    },
    retryable(ATTEMPTS),
    10**9,
)

check("ratio chain delays", [a["delay_ms"] for a in chain], want_delays)
check("ratio chain starts", [a["start_ms"] for a in chain], want_starts)
# 1000 * (7/5)**2 is exactly 1960 and 1000 * (7/5)**3 is exactly 2744; a float
# chain lands a hair below each and truncates to 1959 / 2743.
check("exact power of an inexact ratio", [d for d in want_delays[3:5]], [1960, 2744])
check("attempt 4 delay", chain[3]["delay_ms"], 1960)
check("attempt 5 delay", chain[4]["delay_ms"], 2744)

check(
    "uncapped retry_after",
    plan(
        {"base_ms": 100, "factor": 2, "max_delay_ms": 50, "max_attempts": 3},
        [{"status": 503, "retry_after_ms": 9000}, {"status": 503}, {"status": 200}],
        10**9,
    ),
    [
        {"number": 1, "start_ms": 0, "delay_ms": 0},
        {"number": 2, "start_ms": 9000, "delay_ms": 9000},
        {"number": 3, "start_ms": 9050, "delay_ms": 50},
    ],
)

check(
    "strict deadline",
    [
        a["start_ms"]
        for a in plan(
            {
                "base_ms": 1000,
                "factor": 1,
                "max_delay_ms": 10_000,
                "max_attempts": 6,
            },
            retryable(6),
            3000,
        )
    ],
    [0, 1000, 2000],
)

check(
    "record runs out",
    [
        a["number"]
        for a in plan(
            {"base_ms": 100, "factor": 2, "max_delay_ms": 10_000, "max_attempts": 9},
            retryable(3),
            10**9,
        )
    ],
    [1, 2, 3],
)

try:
    plan(
        {"base_ms": 0, "factor": 2, "max_delay_ms": 10_000, "max_attempts": 3},
        [],
        10**9,
    )
except PolicyError:
    pass
except Exception as exc:  # noqa: BLE001
    failures.append(f"bad base_ms: raised {type(exc).__name__} instead of PolicyError")
else:
    failures.append("bad base_ms: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
