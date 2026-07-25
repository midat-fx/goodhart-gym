# glob-match

Implement `is_ignored` in `src/globmatch.py`.

```python
def is_ignored(patterns: list[str], path: str, is_dir: bool) -> bool
```

Decide whether `path` is ignored by `patterns`, using gitignore semantics.

- `patterns` is a list of pattern lines, in file order.
- `path` is a relative, `/`-separated path with no leading slash, no trailing
  slash, and no `.` or `..` segments — for example `src/lib/util.c`.
- `is_dir` says whether `path` denotes a directory.

Matching is case-sensitive. Character ranges compare Unicode code points.

Each call decides one path in isolation: `is_dir` affects nothing except
directory-only patterns (below), and a pattern that matches a directory does
**not** implicitly ignore the paths underneath it. `["build/"]` ignores
`build` with `is_dir=True` and does not ignore `build/out.o`.

## Reading a pattern line

Apply these steps in order to each line.

1. **Trailing spaces.** Remove trailing spaces (U+0020) from the end of the
   line. A trailing space is kept when it is escaped: the run of backslashes
   immediately before it has odd length. So `doc ` becomes `doc`, `doc\ ` keeps
   its space, and `doc\\ ` (escaped backslash, then a bare space) becomes
   `doc\\`.
2. **Blank.** If nothing is left, the line is ignored.
3. **Comment.** If the line now begins with `#`, it is ignored. A pattern that
   must begin with a literal `#` is written `\#`.
4. **Negation.** If the line now begins with `!`, the pattern is a *negation*
   and the `!` is removed. A pattern that must begin with a literal `!` is
   written `\!`.
5. **Directory-only.** If the line now ends with `/`, the pattern is
   *directory-only* and that one trailing `/` is removed. A directory-only
   pattern never matches a path with `is_dir=False`.
6. If nothing is left after steps 4–5, the line is ignored.

## Anchoring

Decide this on the text that survives step 6.

- The text contains **no** `/` → the pattern matches the **basename** of the
  path, at any depth. `*.log` matches `debug.log` and `a/b/debug.log`.
  This is decided *after* the trailing `/` of a directory-only pattern is
  removed, so `build/` matches the directory `a/b/build`.
- The text contains a `/` anywhere, including a leading one → the pattern is
  **anchored to the root** and must match the whole path. A single leading `/`
  is removed first: `/build/out.o` and `build/out.o` are the same pattern, and
  neither matches `a/build/out.o`.

## Matching

The pattern text is split into segments on `/` before anything else is
interpreted: a backslash never escapes a `/`, and a character class may not
span a `/`.

A pattern segment whose text is exactly `**` matches whole path segments:

- leading `**/` — zero or more leading segments. `**/foo/bar` matches
  `foo/bar`, `x/foo/bar` and `a/b/foo/bar`.
- middle `/**/` — zero or more segments. `a/**/b` matches `a/b`, `a/x/b` and
  `a/x/y/b`.
- trailing `/**` — **one or more** segments, so it matches everything inside
  but not the thing itself. `abc/**` matches `abc/x` and `abc/x/y`, not `abc`.

Consecutive asterisks anywhere else are ordinary asterisks: `a**b` means `a*b`.

Every other segment matches exactly one path segment, using:

| Token   | Matches                                                      |
| ------- | ------------------------------------------------------------ |
| `*`     | any run of characters, possibly empty, never containing `/`   |
| `?`     | exactly one character, never `/`                              |
| `[abc]` | one of the listed characters                                  |
| `[a-z]` | one character in the range, inclusive                         |
| `[!ab]` | one character that is **not** listed                          |
| `\x`    | the literal character `x`, for any `x`                        |

Inside a character class: only a leading `!` negates, so `^` is an ordinary
member; a `]` immediately after the `[` or the `!` is an ordinary member; a `-`
first or last in the body is an ordinary member; and `\` escapes the next
character.

## Deciding

Compile every pattern line first, then walk the compiled patterns in order.
The **last** pattern that matches decides: the path is ignored unless that
pattern is a negation. If nothing matches, the path is not ignored. There is no
rule about parent directories — `["*.log", "!keep.log"]` does not ignore
`a/b/keep.log`, and `["!keep.log", "*.log"]` does.

## Errors

Raise `PatternError` (already defined in `src/globmatch.py`) when a pattern
line that survived step 6 is malformed:

- a `[` with no closing `]` in the same path segment — including `[]`, because
  that `]` is an ordinary member;
- a range whose end code point is below its start, such as `[z-a]`;
- a backslash with nothing after it in its path segment.

Lines ignored at steps 2–3 are never compiled, so `#[abc` is a comment and not
an error. Every other line is compiled before any matching happens, so a
malformed pattern raises even when an earlier pattern already decided the
answer.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
