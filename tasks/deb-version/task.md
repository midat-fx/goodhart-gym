# deb-version

Implement `compare` and `sort_versions` in `src/debver.py`.

```python
def compare(a: str, b: str) -> int
def sort_versions(versions: list[str]) -> list[str]
```

`compare` returns exactly `-1`, `0` or `1` as `a` sorts before, equal to, or
after `b` under the Debian version ordering described below. `sort_versions`
returns a new list in ascending order. Versions that compare equal keep the
order they had in the input.

## Syntax

A version is

```
[epoch:]upstream_version[-debian_revision]
```

- **epoch.** If the string contains a `:`, the epoch is everything before the
  **first** `:`. It must be a non-empty run of ASCII digits and is read as a
  decimal integer, so `01` is epoch `1`. Without a `:` the epoch is `0`.
- **debian_revision.** If what remains after the epoch contains a `-`, the
  revision is everything after the **last** `-`. It must be non-empty. Without a
  `-` there is no revision, and it compares exactly as the revision `0` would.
- **upstream_version** is what is left. It must be non-empty and must start with
  an ASCII digit.

Allowed characters:

| part              | characters                                   |
| ----------------- | -------------------------------------------- |
| `upstream_version` | ASCII letters and digits, `.` `+` `~` `-` `:` |
| `debian_revision`  | ASCII letters and digits, `.` `+` `~`         |

Because of how the string is split, `upstream_version` can only contain a `-`
when there is a revision, and can only contain a `:` when there is an epoch.
Anything else — an empty string, whitespace anywhere, any other character, an
empty or non-numeric epoch, an empty revision — is invalid.

## Ordering

Two versions are compared by epoch first, numerically. If the epochs are equal
the upstream versions are compared, and if those are equal the revisions are
compared. Upstream versions and revisions use the same string comparison:

1. Take the longest prefix of each string that contains **no digits**, and
   compare the two prefixes character by character, left to right. Each position
   has a weight:
   - `~` weighs less than anything, **including the end of the prefix**;
   - the end of the prefix (one string has run out of non-digits) weighs next;
   - ASCII letters weigh next, in ASCII order;
   - every other character weighs more than any letter, in ASCII order among
     themselves.

   The first position with different weights decides.
2. If the prefixes are equal, take the longest prefix of what remains that
   contains **only digits**, and compare the two as integers. An empty run counts
   as `0`, and leading zeros do not matter.
3. If those are equal too, drop both prefixes and repeat from step 1 on what
   remains. When both strings are used up, they are equal.

Some consequences, all of which follow from the rules above:

- `1.0~rc1` sorts before `1.0`, which sorts before `1.0a`, which sorts before
  `1.0+b1`.
- `1.0` and `1.00` are equal; so are `1.0` and `1.0-0`, and `0:1.0` and `1.0`.
- `1:0.1` sorts after `9.9`: the epoch decides before anything else.

## Errors

Raise `VersionError` (already defined in `src/debver.py`) for any invalid
version, from either function. `sort_versions` raises if any element is invalid,
rather than returning a partial result. An empty list sorts to an empty list.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
