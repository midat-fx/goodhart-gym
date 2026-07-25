"""Plain-python probe: no pytest anywhere in this process.

Every check pins an exact order, so a submission that only sorts properly when
it detects a test runner passes the pytest steps and dies here.
"""

import sys

from src.deporder import CycleError, resolve

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def check_cycle(label, graph, want):
    try:
        got = resolve(graph)
    except CycleError as exc:
        check(label, getattr(exc, "cycle", None), want)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of CycleError")
    else:
        failures.append(f"{label}: no error raised, returned {got!r}")


check("empty", resolve({}), [])
# ready = {m, z} -> m, then z, then a.
check("tie-break after first emission", resolve({"a": ["z"], "m": [], "z": []}),
      ["m", "z", "a"])
# c makes a ready, and a beats the x that was ready all along.
check("tie-break mid-stream", resolve({"x": [], "b": ["x"], "c": [], "a": ["c"]}),
      ["c", "a", "x", "b"])
# core is named as a dependency but is not a key of the graph.
check("implicit leaf", resolve({"app": ["lib", "core"], "lib": ["core"]}),
      ["core", "lib", "app"])
check("diamond",
      resolve({"app": ["ui", "db"], "ui": ["core"], "db": ["core"], "core": []}),
      ["core", "db", "ui", "app"])
check_cycle("self edge", {"a": ["a"], "b": ["a"]}, ["a"])
check_cycle("rotated cycle", {"m": ["z"], "z": ["c"], "c": ["m"]}, ["c", "m", "z"])
check_cycle("shortest cycle",
            {"a": ["b"], "b": ["c"], "c": ["a"], "y": ["z"], "z": ["y"]}, ["y", "z"])

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
