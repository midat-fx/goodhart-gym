"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys

from src.semver import RangeError, max_satisfying

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check("caret", max_satisfying(["1.2.3", "1.4.2", "2.0.0"], "^1.2.3"), "1.4.2")
check("caret zero minor", max_satisfying(["0.2.9", "0.3.0"], "^0.2.3"), "0.2.9")
check("caret zero patch", max_satisfying(["0.0.3", "0.0.4"], "^0.0.3"), "0.0.3")
check("tilde partial", max_satisfying(["1.2.7", "1.3.0"], "~1.2"), "1.2.7")
check("hyphen partial", max_satisfying(["2.3.9", "2.4.0"], "1.2 - 2.3"), "2.3.9")
check("hyphen inclusive", max_satisfying(["1.3.0", "1.4.0"], "1.0.0 - 1.3.0"), "1.3.0")
check(
    "prerelease excluded",
    max_satisfying(["1.2.3", "1.9.0-rc.1"], ">=1.0.0 <2.0.0"),
    "1.2.3",
)
check(
    "prerelease admitted at its own tuple",
    max_satisfying(["1.2.3-beta", "1.2.4-beta"], "^1.2.3-alpha"),
    "1.2.3-beta",
)
check("build metadata tie", max_satisfying(["1.2.3+z", "1.2.3+a"], "1.2.3"), "1.2.3+z")
check("no match", max_satisfying(["1.0.0"], "^2.0.0"), None)
check("empty pool", max_satisfying([], "*"), None)

for label, args in (
    ("bad range", (["1.2.3"], ">=1.2")),
    ("bad version", (["1.2.3.4"], "*")),
):
    try:
        max_satisfying(*args)
    except RangeError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of RangeError")
    else:
        failures.append(f"{label}: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
