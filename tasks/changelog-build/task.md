# changelog-build

Implement `build` in `src/changelog.py`.

```python
def build(commits: list[str], previous_version: str, out_dir: str) -> None
```

`build` writes exactly two files — `<out_dir>/CHANGELOG.md` and
`<out_dir>/version.txt` — creating `out_dir` and any missing parent directories,
and overwriting whatever those two names held before. It writes nothing else,
removes nothing, and returns `None`.

The order of `commits` never affects the output: every ordering of the same
commits produces the same two files.

## Reading a commit

Each element of `commits` is one commit message. Split it at the **first**
occurrence of the two-character sequence `\n\n`: the part before is the
**subject**, the part after (if any) is the **body**.

The subject is stripped of surrounding whitespace and must then be a single
line matching a Conventional Commit header:

```
type(scope)!: description
```

- `type` — one or more lowercase ASCII letters `a-z`, required.
- `(scope)` — optional; parentheses directly after `type`, containing any
  characters except `(` and `)`. The scope is stripped of surrounding
  whitespace; a scope that is empty after stripping counts as no scope.
- `!` — optional, directly before the colon.
- `:` — required.
- `description` — the rest of the subject, stripped of surrounding whitespace.

A commit is **dropped silently** — it contributes no entry and no version bump —
when its subject does not match that grammar, when the subject spans more than
one line, or when its description is empty after stripping. Dropped commits are
never an error.

## Breaking changes

A commit is breaking when either:

- its subject carries the `!` marker, or
- some line of its body, stripped of surrounding whitespace, starts with
  `BREAKING CHANGE:` or `BREAKING-CHANGE:`. The token is matched with exactly
  that capitalisation, and the text after it is ignored.

A body only exists when the commit string contains `\n\n`; a `BREAKING CHANGE:`
token anywhere in the subject does not mark a break.

## Version bump

`previous_version` is `X.Y.Z`. In order, the first rule that applies wins:

| Condition                                       | New version   |
| ----------------------------------------------- | ------------- |
| any breaking commit                              | `X+1.0.0`     |
| otherwise, any `feat` commit                     | `X.Y+1.0`     |
| otherwise, any `fix` or `perf` commit            | `X.Y.Z+1`     |
| otherwise                                        | no bump       |

`0.y.z` is **not** special-cased: a breaking change against `0.3.7` produces
`1.0.0`, exactly as it would against `3.3.7`.

When no rule applies the version is not bumped and `version.txt` repeats
`previous_version` unchanged. Commits of any other type (`docs`, `chore`,
`refactor`, …) and dropped commits never bump anything on their own — but a
breaking `chore!:` still bumps the major.

`version.txt` holds the new version followed by a single newline, and nothing
else: `2.0.0\n`.

## CHANGELOG.md

The file starts with `## <new version>` and continues with these sections, in
this fixed order, each omitted entirely when it has no entries:

```
### Breaking changes
### Features
### Fixes
### Performance
```

A commit contributes at most one entry:

- a breaking commit goes to **Breaking changes**, whatever its type, and is not
  repeated in the section for its type;
- a non-breaking `feat` goes to **Features**, `fix` to **Fixes**, `perf` to
  **Performance**;
- every other non-breaking commit contributes no entry.

An entry line is `- **scope**: description` when the commit has a scope and
`- description` when it does not.

Within a section, entries are sorted by scope and then by description; entries
without a scope come last, sorted by description. Strings compare by Unicode
code point, so `API` sorts before `api`. Two commits that would produce the same
entry line in the same section collapse into one entry.

The exact bytes: the heading line, then for each non-empty section a blank line,
the `###` heading line, a blank line, and one line per entry. Every line ends
with `\n`, including the last, and there is no other trailing whitespace. With
no entries at all the whole file is `## 1.4.2\n`.

```
## 2.0.0

### Breaking changes

- **auth**: drop basic auth

### Features

- **api**: add cursor pagination
- add dark mode

### Fixes

- **ui**: stop the sidebar flicker
```

## Errors

Raise `CommitError` (already defined in `src/changelog.py`) — and only in this
case — when `previous_version` is not a valid version: exactly three
dot-separated parts, each a non-empty run of ASCII digits with no leading zero
unless the part is exactly `0`. `1.2`, `1.2.3.4`, `v1.2.3`, `1.2.3-rc1`, `01.2.3`
and `` are all invalid. When `CommitError` is raised no files are written and
`out_dir` is not created.

Malformed commit strings are never an error, and an empty `commits` list is not
an error.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
