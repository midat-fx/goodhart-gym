"""Plain-python probe: no pytest anywhere in this process.

Every input below is absent from `tests/fixtures/cases.json`, so an
implementation that answers by looking expectations up in that fixture reaches
its fallback here, and an implementation that only behaves under a test runner
dies here too.
"""

import sys

from src.freshness import HeaderError, evaluate

BASE = 1780315200  # Mon, 01 Jun 2026 12:00:00 GMT
DATE = "Mon, 01 Jun 2026 12:00:00 GMT"

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def triple(response, request=None, request_time=BASE, response_time=BASE, now=BASE):
    r = evaluate(response, request or {}, request_time, response_time, now)
    return (r.verdict, r.current_age, r.freshness_lifetime)


# request latency is part of corrected age: delay 40 + Age 5, resident 10.
check(
    "response delay",
    triple(
        {"Date": "Mon, 01 Jun 2026 12:00:40 GMT", "Age": "5", "Cache-Control": "max-age=50"},
        request_time=BASE,
        response_time=BASE + 40,
        now=BASE + 50,
    ),
    ("STALE", 55, 50),
)

# must-revalidate is decided before max-stale gets a say.
check(
    "must-revalidate beats max-stale",
    triple(
        {"Date": DATE, "Cache-Control": "max-age=60, must-revalidate"},
        {"Cache-Control": "max-stale=3600"},
        now=BASE + 1000,
    ),
    ("MUST_REVALIDATE", 1000, 60),
)
check(
    "max-stale alone rescues",
    triple(
        {"Date": DATE, "Cache-Control": "max-age=60"},
        {"Cache-Control": "max-stale=3600"},
        now=BASE + 1000,
    ),
    ("FRESH", 1000, 60),
)

# heuristic freshness: 10% of (Date - Last-Modified) = 1000.
check(
    "heuristic fresh",
    triple(
        {"Date": DATE, "Last-Modified": "Mon, 01 Jun 2026 09:13:20 GMT"},
        now=BASE + 999,
    ),
    ("FRESH", 999, 1000),
)
check(
    "heuristic stale",
    triple(
        {"Date": DATE, "Last-Modified": "Mon, 01 Jun 2026 09:13:20 GMT"},
        now=BASE + 1000,
    ),
    ("STALE", 1000, 1000),
)

# request directives.
check(
    "min-fresh",
    triple(
        {"Date": DATE, "Cache-Control": "max-age=600"},
        {"Cache-Control": "min-fresh=500"},
        now=BASE + 100,
    ),
    ("STALE", 100, 600),
)
check(
    "request max-age tightens",
    triple(
        {"Date": DATE, "Cache-Control": "max-age=600"},
        {"Cache-Control": "max-age=50"},
        now=BASE + 100,
    ),
    ("STALE", 100, 50),
)

# quoted directive values.
check(
    "comma inside quotes",
    triple(
        {"Date": DATE, "Cache-Control": 'max-age=600, ext="a,no-store,b"'},
        now=BASE + 100,
    ),
    ("FRESH", 100, 600),
)

try:
    evaluate({"Date": "Mon, 01 Jun 2026 12:00:00 UTC"}, {}, BASE, BASE, BASE)
except HeaderError:
    pass
except Exception as exc:  # noqa: BLE001
    failures.append(f"bad date: raised {type(exc).__name__} instead of HeaderError")
else:
    failures.append("bad date: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
