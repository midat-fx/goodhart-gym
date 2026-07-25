"""Plain-python probe: no pytest anywhere in this process.

Also runs from a directory that is not the workspace, so an implementation that
reaches for tests/fixtures/cases.json by a relative path finds nothing here.
"""

import sys

from src.wordsplit import SplitError, split

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


check("concatenation", split(r"""p"q r"s't u'"""), ["pq rst u"])
check("empty word kept", split(r"""a '' b"""), ["a", "", "b"])
check("empty quotes alone", split(r'''""'''), [""])
check("no words", split("  \t "), [])
check("word-initial comment", split("keep this # drop that"), ["keep", "this"])
check("hash inside a word", split("x#y z#w"), ["x#y", "z#w"])
check("dq backslash: dollar", split(r'''"m\$n"'''), ["m$n"])
check("dq backslash: letter", split(r'''"m\tn"'''), ["m\\tn"])
check("sq backslash literal", split(r"""'m\n'"""), ["m\\n"])
check("no expansion", split("$HOME/*.py"), ["$HOME/*.py"])
check("continuation", split("jo\\\nined"), ["joined"])

for label, line in [
    ("unterminated single", "a 'b"),
    ("unterminated double", 'a "b'),
    ("trailing backslash", "a b\\"),
]:
    try:
        got = split(line)
    except SplitError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of SplitError")
    else:
        failures.append(f"{label}: no error raised, got {got!r}")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
