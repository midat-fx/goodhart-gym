# json-patch

Implement `apply` in `src/jsonpatch.py`.

```python
def apply(document: Any, patch: list[dict]) -> Any
```

Apply a JSON Patch (RFC 6902) to a JSON document and return the result. The
document is any JSON value as Python decodes it: `dict`, `list`, `str`, `int`,
`float`, `bool` or `None`. The patch is a list of operation objects applied in
order, each one to the result of the previous one.

## The input is never modified

`apply` must not modify `document` or `patch`, whether it succeeds or fails, and
the value it returns must not share any `dict` or `list` with either of them —
changing the result afterwards must never change the inputs, and the other way
round. On failure it raises and returns nothing, so a patch is all-or-nothing.

## Pointers (RFC 6901)

`path` and `from` are JSON Pointers:

- The empty string `""` refers to the whole document.
- Any other pointer must start with `/`. It is split on `/` into reference
  tokens; in each token `~1` stands for `/` and `~0` for `~`, decoded in that
  order, so `~01` is the literal `~1`. A `~` followed by anything other than `0`
  or `1`, or at the end of a token, is an error.
- In an object a token is a member name; any string is a valid name, including
  the empty one (`"/"` refers to the member named `""`).
- In an array a token must be `0` or a run of ASCII digits with no leading zero,
  and it is an index. The token `-` refers to the position just past the last
  element. It is only meaningful as the target of `add` (and of the `add` half of
  `move` and `copy`); anywhere else it does not exist.
- A pointer that tries to descend into a string, number, boolean or null is an
  error.

## Operations

Every operation is a `dict` with a string member `op` and a string member
`path`. Other members are required as listed below; members not listed are
ignored.

| `op`      | needs   | does                                                                                     |
| --------- | ------- | ---------------------------------------------------------------------------------------- |
| `add`     | `value` | Adds `value` at `path`. See below.                                                        |
| `remove`  |         | Removes the value at `path`, which must exist.                                            |
| `replace` | `value` | Replaces the value at `path`, which must exist.                                           |
| `move`    | `from`  | Removes the value at `from` and adds it at `path`, exactly as `remove` then `add` would.  |
| `copy`    | `from`  | Adds a copy of the value at `from` at `path`, exactly as `add` would.                     |
| `test`    | `value` | Succeeds if the value at `path` is equal to `value`, and fails otherwise.                 |

`value` may be any JSON value, including `None`; what matters is that the
member is present.

**add.** If `path` is `""`, the whole document is replaced by `value`. Otherwise
the parent of `path` — everything but the last token — must exist and be an
object or an array. In an object the member is added, or replaced if it is
already there. In an array the value is inserted **before** the given index,
shifting later elements up; the index may be anything from `0` to the length of
the array, inclusive, and `-` appends.

**remove.** Removing from an array shifts later elements down. Removing `""`
(the whole document) is an error.

**replace.** Replacing `""` replaces the whole document with `value`.

**move.** `from` must exist. It is an error if `from` is a proper prefix of
`path` — moving a value into one of its own children — which means `path` starts
with `from` followed by `/`. Moving a value to where it already is
(`from == path`) is allowed and changes nothing. Otherwise, the value is removed
from `from` first, and then added at `path` against the document as it is
**after** the removal; array indexes in `path` are read after the shift.

**copy.** The copy is deep: later operations on either location do not affect the
other.

**test.** Equality is JSON equality:

- strings, `None`, `True` and `False` are equal only to themselves;
- numbers are equal when they have the same mathematical value, so `1` equals
  `1.0`, but `True` and `False` are **not** numbers and are never equal to `1` or
  `0`;
- arrays are equal when they have the same length and their elements are equal
  in order;
- objects are equal when they have the same member names and the values of each
  member are equal, in any order.

## Errors

Raise `PatchError` (already defined in `src/jsonpatch.py`) when:

- `patch` is not a list, or one of its elements is not a `dict`;
- `op` is missing, is not a string, or is not one of the six above;
- `path` is missing or is not a string, or `from` is required and is missing or
  is not a string, or `value` is required and missing;
- a pointer is malformed or refers to something that does not exist where it
  must exist;
- an array index is out of range for the operation;
- a `move` would move a value into one of its own children;
- a `test` fails.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
