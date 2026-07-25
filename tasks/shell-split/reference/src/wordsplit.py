"""POSIX-style word splitting with quoting and no expansions. See task.md."""

from __future__ import annotations

SEPARATORS = " \t"

# Inside double quotes a backslash only escapes these five. A newline after the
# backslash is a line continuation: both characters vanish.
DQ_ESCAPABLE = "$`\"\\\n"


class SplitError(ValueError):
    """Raised for an unterminated quote or a lone trailing backslash."""


def split(line: str) -> list[str]:
    """Split `line` into words. See task.md for the rules."""
    words: list[str] = []
    word: list[str] = []
    # Distinct from `word` being empty: '' opens a word without adding to it.
    open_word = False

    i = 0
    n = len(line)
    while i < n:  # every branch advances i, so this always terminates
        ch = line[i]

        if ch in SEPARATORS:
            if open_word:
                words.append("".join(word))
                word = []
                open_word = False
            i += 1

        elif ch == "#" and not open_word:
            break  # comment: the rest of the input is discarded

        elif ch == "\\":
            if i + 1 >= n:
                raise SplitError("lone trailing backslash")
            nxt = line[i + 1]
            i += 2
            if nxt == "\n":
                continue  # line continuation: does not open a word
            word.append(nxt)
            open_word = True

        elif ch == "'":
            end = line.find("'", i + 1)
            if end < 0:
                raise SplitError("unterminated single quote")
            word.append(line[i + 1 : end])
            open_word = True
            i = end + 1

        elif ch == '"':
            i += 1
            open_word = True
            while True:  # bounded by n: i grows every pass, i >= n raises
                if i >= n:
                    raise SplitError("unterminated double quote")
                c = line[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and i + 1 < n and line[i + 1] in DQ_ESCAPABLE:
                    if line[i + 1] != "\n":
                        word.append(line[i + 1])
                    i += 2
                    continue
                word.append(c)
                i += 1

        else:
            word.append(ch)
            open_word = True
            i += 1

    if open_word:
        words.append("".join(word))
    return words
