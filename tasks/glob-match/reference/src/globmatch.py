"""gitignore-style pattern matching. See task.md."""

from __future__ import annotations


class PatternError(ValueError):
    """Raised for a malformed character class or a dangling escape."""


# ---------------------------------------------------------------- line reading


def _strip_trailing_spaces(line: str) -> str:
    """Drop trailing U+0020 unless escaped by an odd run of backslashes."""
    end = len(line)
    while end > 0 and line[end - 1] == " ":
        slashes = 0
        i = end - 2
        while i >= 0 and line[i] == "\\":
            slashes += 1
            i -= 1
        if slashes % 2 == 1:
            break
        end -= 1
    return line[:end]


# ------------------------------------------------------------ segment compiler
#
# A compiled segment is a list of tokens:
#   ("lit", ch)                     one literal character
#   ("any",)                        exactly one character
#   ("star",)                       any run of characters, possibly empty
#   ("class", negated, ((lo, hi),)) one character in / not in the ranges


def _class_member(seg: str, i: int) -> tuple[str, int]:
    """Read one (possibly escaped) class member character starting at i."""
    if seg[i] == "\\":
        if i + 1 >= len(seg):
            raise PatternError(f"dangling escape in character class: {seg!r}")
        return seg[i + 1], i + 2
    return seg[i], i + 1


def _compile_class(seg: str, i: int) -> tuple[tuple, int]:
    """Compile the class starting at seg[i] == '['. Return (token, next index)."""
    j = i + 1
    negated = False
    if j < len(seg) and seg[j] == "!":
        negated = True
        j += 1
    ranges: list[tuple[str, str]] = []
    first = True
    while j < len(seg):
        if seg[j] == "]" and not first:
            return ("class", negated, tuple(ranges)), j + 1
        first = False
        low, j = _class_member(seg, j)
        # "a-z" is a range; a '-' just before the closing ']' is a literal.
        if j + 1 < len(seg) and seg[j] == "-" and seg[j + 1] != "]":
            high, j = _class_member(seg, j + 1)
            if ord(high) < ord(low):
                raise PatternError(f"reversed range [{low}-{high}] in {seg!r}")
            ranges.append((low, high))
        else:
            ranges.append((low, low))
    raise PatternError(f"unterminated character class: {seg!r}")


def _compile_segment(seg: str) -> list[tuple]:
    tokens: list[tuple] = []
    i = 0
    while i < len(seg):
        ch = seg[i]
        if ch == "\\":
            if i + 1 >= len(seg):
                raise PatternError(f"dangling escape: {seg!r}")
            tokens.append(("lit", seg[i + 1]))
            i += 2
        elif ch == "*":
            # Consecutive asterisks inside a segment collapse to one.
            if not tokens or tokens[-1][0] != "star":
                tokens.append(("star",))
            i += 1
        elif ch == "?":
            tokens.append(("any",))
            i += 1
        elif ch == "[":
            token, i = _compile_class(seg, i)
            tokens.append(token)
        else:
            tokens.append(("lit", ch))
            i += 1
    return tokens


def _token_matches(token: tuple, ch: str) -> bool:
    kind = token[0]
    if kind == "lit":
        return ch == token[1]
    if kind == "any":
        return True
    inside = any(ord(lo) <= ord(ch) <= ord(hi) for lo, hi in token[2])
    return inside != token[1]


def _match_segment(tokens: list[tuple], text: str) -> bool:
    """Match one compiled segment against one path segment."""
    n = len(text)
    reach = [False] * (n + 1)
    reach[0] = True
    for token in tokens:
        nxt = [False] * (n + 1)
        if token[0] == "star":
            seen = False
            for i in range(n + 1):
                seen = seen or reach[i]
                nxt[i] = seen
        else:
            for i in range(n):
                if reach[i] and _token_matches(token, text[i]):
                    nxt[i + 1] = True
        reach = nxt
    return reach[n]


# ------------------------------------------------------------ pattern compiler
#
# A compiled pattern is (negated, dir_only, anchored, segments) where a segment
# is either the marker "**" or a list of tokens.


def _compile_pattern(line: str):
    text = _strip_trailing_spaces(line)
    if not text or text[0] == "#":
        return None

    negated = text[0] == "!"
    if negated:
        text = text[1:]

    dir_only = text.endswith("/")
    if dir_only:
        text = text[:-1]
    if not text:
        return None

    anchored = "/" in text
    if not anchored:
        return (negated, dir_only, False, [_compile_segment(text)])

    if text.startswith("/"):
        text = text[1:]
    segments = [
        "**" if part == "**" else _compile_segment(part) for part in text.split("/")
    ]
    return (negated, dir_only, True, segments)


def _match_anchored(segments: list, parts: list[str]) -> bool:
    """Match segments against the whole path, '**' spanning whole segments."""
    n = len(parts)
    # reach[j] is True when segments[i:] can match parts[j:].
    reach = [False] * (n + 1)
    reach[n] = True
    for i in range(len(segments) - 1, -1, -1):
        nxt = [False] * (n + 1)
        segment = segments[i]
        if segment == "**":
            if i == len(segments) - 1:
                # A trailing '**' must consume at least one segment.
                for j in range(n + 1):
                    nxt[j] = j < n
            else:
                seen = False
                for j in range(n, -1, -1):
                    seen = seen or reach[j]
                    nxt[j] = seen
        else:
            for j in range(n):
                if reach[j + 1] and _match_segment(segment, parts[j]):
                    nxt[j] = True
        reach = nxt
    return reach[0]


def is_ignored(patterns: list[str], path: str, is_dir: bool) -> bool:
    """Return True when `path` is ignored by `patterns`."""
    compiled = [c for c in (_compile_pattern(line) for line in patterns) if c]
    parts = path.split("/")

    ignored = False
    for negated, dir_only, anchored, segments in compiled:
        if dir_only and not is_dir:
            continue
        if anchored:
            hit = _match_anchored(segments, parts)
        else:
            hit = _match_segment(segments[0], parts[-1])
        if hit:
            ignored = not negated
    return ignored
