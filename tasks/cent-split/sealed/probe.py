"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys

from src.split import allocate

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check("three-way tie, one cent", allocate(100, [1, 1, 1]), [34, 33, 33])
check("three-way tie, two cents", allocate(200, [1, 1, 1]), [67, 67, 66])
check("largest remainder", allocate(11, [1, 2, 4]), [2, 3, 6])
check("zero weight", allocate(7, [0, 2, 5]), [0, 2, 5])
try:
    allocate(10, [0, 0])
    failures.append("all-zero weights: no ValueError")
except ValueError:
    pass

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("probe ok")
