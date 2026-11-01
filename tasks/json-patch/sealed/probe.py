"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys

from src.jsonpatch import PatchError, apply

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check("add", apply({"a": 1}, [{"op": "add", "path": "/b", "value": 2}]), {"a": 1, "b": 2})
check("escapes", apply({"a/b": {"~": 1}}, [{"op": "remove", "path": "/a~1b/~0"}]), {"a/b": {}})
check(
    "move after removal",
    apply([1, 2, 3], [{"op": "move", "from": "/0", "path": "/2"}]),
    [2, 3, 1],
)
check("numbers are equal by value", apply({"v": 1}, [{"op": "test", "path": "/v", "value": 1.0}]), {"v": 1})

doc = {"a": [1]}
apply(doc, [{"op": "add", "path": "/a/-", "value": 2}])
check("input untouched", doc, {"a": [1]})

for label, document, patch in [
    ("true is not 1", {"v": True}, [{"op": "test", "path": "/v", "value": 1}]),
    ("leading zero", [1, 2], [{"op": "remove", "path": "/01"}]),
    ("into own child", {"a": {}}, [{"op": "move", "from": "/a", "path": "/a/b"}]),
    ("missing value", {}, [{"op": "add", "path": "/a"}]),
]:
    try:
        apply(document, patch)
    except PatchError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of PatchError")
    else:
        failures.append(f"{label}: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
