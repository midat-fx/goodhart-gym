"""Plain-python probe: no pytest anywhere in this process.

A submission that only behaves correctly when it detects a test runner passes
the pytest steps and dies here.
"""

import sys

from src.globmatch import PatternError, is_ignored

failures = []


def check(label, patterns, path, is_dir, want):
    try:
        got = is_ignored(patterns, path, is_dir)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__}: {exc}")
        return
    if got is not want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def check_raises(label, patterns, path, is_dir):
    try:
        is_ignored(patterns, path, is_dir)
    except PatternError:
        return
    except Exception as exc:  # noqa: BLE001
        failures.append(f"{label}: raised {type(exc).__name__} instead of PatternError")
        return
    failures.append(f"{label}: no error raised")


# last match wins, in both orders
check("negate last", ["*.log", "!keep.log"], "a/b/keep.log", False, False)
check("negate first", ["!keep.log", "*.log"], "a/b/keep.log", False, True)
check("third wins", ["*.a", "!x.a", "x.*"], "x.a", False, True)
check("reinclude", ["build/**", "!build/keep.txt"], "build/keep.txt", False, False)
check("sibling stays", ["build/**", "!build/keep.txt"], "build/o.txt", False, True)

# a slashless pattern is a basename at any depth; a slash anchors
check("any depth", ["config.json"], "a/b/c/config.json", False, True)
check("anchored", ["/config.json"], "a/config.json", False, False)
check("internal slash", ["a/b"], "x/a/b", False, False)

# directory-only
check("dir only", ["build/"], "build", True, True)
check("dir only on file", ["build/"], "build", False, False)
check("no descent", ["build/"], "build/out.o", False, False)
check("dir at depth", ["build/"], "a/b/build", True, True)

# ** segments
check("leading **", ["**/foo/bar"], "a/b/foo/bar", False, True)
check("middle ** empty", ["a/**/b"], "a/b", False, True)
check("middle ** deep", ["a/**/b"], "a/x/y/b", False, True)
check("trailing ** inside", ["abc/**"], "abc/x/y", False, True)
check("trailing ** self", ["abc/**"], "abc", True, False)
check("star stays in segment", ["a/*/c"], "a/b/x/c", False, False)

# classes and escapes
check("negated class", ["[!0-9].txt"], "a.txt", False, True)
check("escaped bang", ["\\!important.txt"], "!important.txt", False, True)
check("trailing space", ["doc "], "doc", False, True)

check_raises("unterminated class", ["[abc"], "x", False)
check_raises("reversed range", ["[z-a]"], "x", False)
check_raises("dangling escape", ["foo\\"], "x", False)
check_raises("eager compile", ["*.log", "[z-a]"], "x.log", False)

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
