"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys
from datetime import datetime

from src.duration import Duration, DurationError, add, format, parse

failures = []


def check(label, call, want):
    """`call` is a zero-argument callable so a raise is reported, not fatal."""
    try:
        got = call()
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__}: {exc}")
        return
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def check_raises(label, text):
    try:
        got = parse(text)
    except DurationError:
        return
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of DurationError")
        return
    failures.append(f"{label}: no error raised, got {got!r}")


check("clamp", lambda: add(datetime(2026, 1, 31), parse("P1M")), datetime(2026, 2, 28))
check(
    "clamp leap",
    lambda: add(datetime(2028, 1, 31), parse("P1M")),
    datetime(2028, 2, 29),
)
check(
    "clamp once",
    lambda: add(datetime(2028, 2, 29), parse("P1Y1M")),
    datetime(2029, 3, 29),
)
check(
    "clamp then day",
    lambda: add(datetime(2026, 1, 31), parse("P1M1D")),
    datetime(2026, 3, 1),
)
check(
    "negative",
    lambda: add(datetime(2026, 3, 31, 9), parse("-P1M")),
    datetime(2026, 2, 28, 9),
)

check("weeks", lambda: parse("P2W"), Duration(days=14))
check("fraction", lambda: parse("PT1.5H"), Duration(hours=1, minutes=30))
check("comma fraction", lambda: parse("PT0,5S"), Duration(microseconds=500_000))

check("months", lambda: format(Duration(months=2)), "P2M")
check("minutes", lambda: format(Duration(minutes=2)), "PT2M")
check("zero", lambda: format(Duration()), "PT0S")
check("no week form", lambda: format(Duration(days=14)), "P14D")
check("micros", lambda: format(Duration(seconds=1, microseconds=500_000)), "PT1.5S")
check("round trip", lambda: format(parse("-P1Y2M3DT4H5M6S")), "-P1Y2M3DT4H5M6S")

check_raises("bare P", "P")
check_raises("week combined", "P1W1D")
check_raises("fractional months", "P1.5M")
check_raises("fraction not last", "P1.5DT1H")
check_raises("time without T", "P1H")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
