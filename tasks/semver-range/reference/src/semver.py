"""Highest version in a list satisfying an npm-style range. See task.md."""

from __future__ import annotations

import re

_NUM = r"0|[1-9][0-9]*"
_IDENT = r"[0-9A-Za-z-]+"
_DOTTED = rf"{_IDENT}(?:\.{_IDENT})*"
_VERSION = re.compile(
    rf"(?P<major>{_NUM})\.(?P<minor>{_NUM})\.(?P<patch>{_NUM})"
    rf"(?:-(?P<pre>{_DOTTED}))?"
    rf"(?:\+(?P<build>{_DOTTED}))?"
)
_PLAIN_NUM = re.compile(_NUM)

_WILDCARDS = {"x", "X", "*"}
_OPERATORS = (">=", "<=", ">", "<", "=", "^", "~")


class RangeError(ValueError):
    """Raised for malformed range expressions and malformed versions."""


# --- versions ---------------------------------------------------------------


def _parse_version(text: str) -> tuple[int, int, int, tuple[str, ...] | None]:
    """Parse a fully specified version. Build metadata is validated, then dropped."""
    if not isinstance(text, str):
        raise RangeError(f"not a version: {text!r}")
    match = _VERSION.fullmatch(text)
    if match is None:
        raise RangeError(f"malformed version: {text!r}")
    pre = match.group("pre")
    if pre is None:
        idents = None
    else:
        idents = tuple(pre.split("."))
        for ident in idents:
            if ident.isdigit() and len(ident) > 1 and ident[0] == "0":
                raise RangeError(f"leading zero in prerelease: {text!r}")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        idents,
    )


def _ident_key(ident: str) -> tuple[int, int, str]:
    if ident.isdigit():
        return (0, int(ident), "")
    return (1, 0, ident)


def _key(version) -> tuple:
    major, minor, patch, pre = version
    if pre is None:
        return (major, minor, patch, 1, ())
    return (major, minor, patch, 0, tuple(_ident_key(i) for i in pre))


_TESTS = {
    "=": lambda a, b: a == b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


# --- comparators ------------------------------------------------------------


def _parse_partial(text: str) -> tuple[list[int], tuple[str, ...] | None]:
    """Return (specified components, prerelease) for a possibly partial version."""
    if text in _WILDCARDS or text == "":
        return [], None
    match = _VERSION.fullmatch(text)
    if match is not None:
        major, minor, patch, pre = _parse_version(text)
        return [major, minor, patch], pre
    if "-" in text or "+" in text:
        raise RangeError(f"malformed version in range: {text!r}")

    nums: list[int] = []
    seen_wildcard = False
    parts = text.split(".")
    if len(parts) > 3:
        raise RangeError(f"too many components: {text!r}")
    for part in parts:
        if part in _WILDCARDS:
            seen_wildcard = True
            continue
        if seen_wildcard or _PLAIN_NUM.fullmatch(part) is None:
            raise RangeError(f"malformed version in range: {text!r}")
        nums.append(int(part))
    return nums, None


def _bump(nums: list[int], index: int) -> tuple[int, int, int, None]:
    out = list(nums) + [0] * (3 - len(nums))
    out[index] += 1
    for j in range(index + 1, 3):
        out[j] = 0
    return (out[0], out[1], out[2], None)


def _low(nums: list[int], pre) -> tuple[int, int, int, tuple[str, ...] | None]:
    out = list(nums) + [0] * (3 - len(nums))
    return (out[0], out[1], out[2], pre)


def _comparator(token: str) -> list[tuple[str, tuple]]:
    """Desugar one comparator token into primitive (op, version) pairs."""
    op = ""
    for candidate in _OPERATORS:
        if token.startswith(candidate):
            op = candidate
            break
    body = token[len(op):]
    if op and not body:
        raise RangeError(f"comparator without a version: {token!r}")

    nums, pre = _parse_partial(body)

    if op in (">", ">=", "<", "<="):
        if len(nums) != 3:
            raise RangeError(f"{op} needs a fully specified version: {token!r}")
        return [(op, _low(nums, pre))]

    if op in ("^", "~"):
        if not nums:
            raise RangeError(f"{op} needs at least a major version: {token!r}")
        if op == "^":
            index = next(
                (i for i, n in enumerate(nums) if n != 0), len(nums) - 1
            )
        else:
            index = 1 if len(nums) >= 2 else 0
        return [(">=", _low(nums, pre)), ("<", _bump(nums, index))]

    # bare or "="
    if not nums:
        return [(">=", (0, 0, 0, None))]
    if len(nums) == 3:
        return [("=", _low(nums, pre))]
    return [(">=", _low(nums, pre)), ("<", _bump(nums, len(nums) - 1))]


def _hyphen(low_text: str, high_text: str) -> list[tuple[str, tuple]]:
    low_nums, low_pre = _parse_partial(low_text)
    high_nums, high_pre = _parse_partial(high_text)
    if not low_nums or not high_nums:
        raise RangeError("hyphen range needs a major version on both sides")
    out = [(">=", _low(low_nums, low_pre))]
    if len(high_nums) == 3:
        out.append(("<=", _low(high_nums, high_pre)))
    else:
        out.append(("<", _bump(high_nums, len(high_nums) - 1)))
    return out


def _comparator_set(text: str) -> list[tuple[str, tuple]]:
    tokens = text.split()
    if not tokens:
        raise RangeError("empty comparator set")
    if "-" in tokens:
        if len(tokens) != 3 or tokens[1] != "-":
            raise RangeError(f"malformed hyphen range: {text!r}")
        return _hyphen(tokens[0], tokens[2])
    out: list[tuple[str, tuple]] = []
    for token in tokens:
        out.extend(_comparator(token))
    return out


def _parse_range(range_expr: str) -> list[list[tuple[str, tuple]]]:
    if not isinstance(range_expr, str):
        raise RangeError(f"not a range: {range_expr!r}")
    if not range_expr.strip():
        return [[(">=", (0, 0, 0, None))]]
    return [_comparator_set(part) for part in range_expr.split("||")]


# --- matching ---------------------------------------------------------------


def _satisfies(version, comparators: list[tuple[str, tuple]]) -> bool:
    version_key = _key(version)
    for op, other in comparators:
        if not _TESTS[op](version_key, _key(other)):
            return False
    if version[3] is None:
        return True
    return any(
        other[3] is not None and other[:3] == version[:3] for _, other in comparators
    )


def max_satisfying(versions: list[str], range_expr: str) -> str | None:
    """Return the highest version in `versions` that satisfies `range_expr`."""
    sets = _parse_range(range_expr)

    best: str | None = None
    best_key: tuple | None = None
    for text in versions:
        version = _parse_version(text)
        if not any(_satisfies(version, comparators) for comparators in sets):
            continue
        key = _key(version)
        if best_key is None or key > best_key:
            best, best_key = text, key
    return best
