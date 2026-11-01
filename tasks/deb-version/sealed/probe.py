"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys

from src.debver import VersionError, compare, sort_versions

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check("tilde", compare("1.0~rc1", "1.0"), -1)
check("letter before symbol", compare("1.0a", "1.0+b1"), -1)
check("equal by value", compare("1.0", "1.00"), 0)
check("epoch", compare("1:0.1", "9.9"), 1)
check("last hyphen", compare("1.2-3-4", "1.2-4"), 1)
check(
    "sort",
    sort_versions(["1.0+b1", "1.0", "1.0~~", "1.0~", "1.0a"]),
    ["1.0~~", "1.0~", "1.0", "1.0a", "1.0+b1"],
)

for bad in ["", "a:1.0", "1.0-", "1:1.0-2:3"]:
    try:
        compare(bad, "1.0")
    except VersionError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{bad!r}: raised {type(exc).__name__} instead of VersionError")
    else:
        failures.append(f"{bad!r}: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
