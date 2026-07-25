"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys

from src.bucket import ConfigError, Event, decide

CONFIG = {"capacity": 5, "refill_tokens": 3, "refill_interval_ms": 1000}

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check(
    "drain then deny",
    decide(CONFIG, [Event(0, "a", 1)] * 5 + [Event(0, "a", 3)]),
    [(True, 4, 0), (True, 3, 0), (True, 2, 0), (True, 1, 0), (True, 0, 0), (False, 0, 1000)],
)
check(
    "cost above capacity",
    decide(CONFIG, [Event(0, "a", 6), Event(0, "a", 5)]),
    [(False, 5, -1), (True, 0, 0)],
)
check(
    "retry rounds up",
    decide({**CONFIG, "initial_tokens": 0}, [Event(0, "a", 1)]),
    [(False, 0, 334)],
)
check(
    "capacity clamps an idle bucket",
    decide(CONFIG, [Event(0, "a", 5), Event(10**9, "a", 5), Event(10**9, "a", 1)]),
    [(True, 0, 0), (True, 0, 0), (False, 0, 334)],
)

# Exact refill: 13/1100 tokens per ms lands on exactly 13 tokens at 1100ms,
# after 23 events have each nudged the count by a fraction of a token.
drift = {"capacity": 15, "refill_tokens": 13, "refill_interval_ms": 1100, "initial_tokens": 0}
times = {t: 0 for t in range(0, 1101, 49)}
times[1100] = 13
check(
    "exact fractional refill",
    decide(drift, [Event(t, "poll", c) for t, c in sorted(times.items())])[-1],
    (True, 0, 0),
)

for label, config, events in [
    ("capacity", {**CONFIG, "capacity": 0}, []),
    ("unsorted", CONFIG, [Event(5, "a", 1), Event(4, "a", 1)]),
    ("negative cost", CONFIG, [Event(0, "a", -2)]),
]:
    try:
        decide(config, events)
    except ConfigError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of ConfigError")
    else:
        failures.append(f"{label}: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
