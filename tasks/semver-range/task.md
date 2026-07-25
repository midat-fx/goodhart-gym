# semver-range

Implement `max_satisfying` in `src/semver.py`.

```python
def max_satisfying(versions: list[str], range_expr: str) -> str | None
```

Return the entry of `versions` with the highest precedence that satisfies the
npm-style range `range_expr`, or `None` if no entry satisfies it. The value
returned is the input string unchanged, never a normalised form. When two
satisfying entries have equal precedence — they can only differ in build
metadata — return the one that appears **first** in `versions`.

Every entry of `versions` is validated, whether or not it would have matched.
An empty `versions` list gives `None`.

## Versions

```
version := MAJOR "." MINOR "." PATCH [ "-" PRERELEASE ] [ "+" BUILD ]
```

- `MAJOR`, `MINOR`, `PATCH` are decimal integers with no leading zeros (`0` is
  the only numeral that may start with `0`). All three are required.
- `PRERELEASE` is one or more dot-separated identifiers. Each identifier is
  non-empty and drawn from `[0-9A-Za-z-]`. An identifier that is all digits
  must not have a leading zero.
- `BUILD` is one or more dot-separated identifiers drawn from `[0-9A-Za-z-]`.
  Leading zeros are allowed here.
- No leading `v`, and no surrounding whitespace. Anything else is malformed.

### Precedence

Compare `MAJOR`, then `MINOR`, then `PATCH`, numerically. Build metadata is
ignored entirely: `1.2.3+a` and `1.2.3+b` have equal precedence, and both have
the same precedence as `1.2.3`.

If major, minor and patch are equal, then:

- a version **with** a prerelease has lower precedence than the same version
  **without** one (`1.2.3-rc.1` < `1.2.3`);
- otherwise compare prerelease identifiers left to right:
  - two all-digit identifiers compare numerically (`alpha.2` < `alpha.11`);
  - an all-digit identifier is always lower than an identifier that is not
    (`1.2.3-alpha.9` < `1.2.3-alpha.beta`);
  - two non-digit identifiers compare by ASCII ordering;
  - if one prerelease is a prefix of the other, the longer one is higher
    (`1.2.3-alpha` < `1.2.3-alpha.1`).

## Ranges

A range expression is one or more **comparator sets** joined by `||`. A version
satisfies the expression when it satisfies at least one comparator set.

A comparator set is either a hyphen range or a whitespace-separated list of
comparators, all of which must be satisfied (they are ANDed). A comparator
never contains whitespace of its own, so `> 1.2.3` is two tokens and is
malformed.

Every comparator form below desugars into **primitive comparators** — an
operator from `= > >= < <=` followed by a fully specified version. Matching and
the prerelease rule are both defined over the desugared primitives.

### Partial versions

A comparator's version may be partial: components may be dropped from the right
(`1.2`, `1`), or written as `x`, `X` or `*`. A wildcard component makes every
component to its right a wildcard too, so `1.x.3` is malformed. A prerelease or
build suffix may only appear on a fully specified `MAJOR.MINOR.PATCH`, so
`1.2-beta` is malformed.

Call the components actually given the *specified* ones; unspecified components
read as `0` when a lower bound is formed.

### Comparator forms

| Form            | Desugars to                                                   |
| --------------- | ------------------------------------------------------------- |
| `1.2.3`, `=1.2.3` | `=1.2.3`                                                    |
| `1.2`, `=1.2`, `1.2.x` | `>=1.2.0 <1.3.0`                                       |
| `1`, `1.x`, `1.x.x` | `>=1.0.0 <2.0.0`                                          |
| `*`, `x`, `X`, and the empty expression | `>=0.0.0`                             |
| `>1.2.3` `>=1.2.3` `<1.2.3` `<=1.2.3` | itself                                  |
| `^…`            | see below                                                     |
| `~…`            | see below                                                     |

`>`, `>=`, `<` and `<=` require a fully specified version: `>=1.2` and `>=1.2.x`
are malformed.

For a bare or `=` comparator with a partial version, the upper bound increments
the **last specified** component and zeroes everything to its right.

### Caret

`^` needs at least a major component (`^` and `^*` are malformed). The lower
bound is the version completed with zeros, keeping its prerelease if it has one.
For the upper bound, take the **leftmost specified component that is non-zero**;
if every specified component is zero, take the **last specified** one. Increment
that component and zero everything to its right.

```
^1.2.3  →  >=1.2.3 <2.0.0        ^1.2  →  >=1.2.0 <2.0.0
^0.2.3  →  >=0.2.3 <0.3.0        ^0.2  →  >=0.2.0 <0.3.0
^0.0.3  →  >=0.0.3 <0.0.4        ^0.0  →  >=0.0.0 <0.1.0
^0.0.0  →  >=0.0.0 <0.0.1        ^0    →  >=0.0.0 <1.0.0
^1.2.3-beta.2  →  >=1.2.3-beta.2 <2.0.0
```

### Tilde

`~` needs at least a major component. The lower bound is formed the same way. If
a minor component was specified the upper bound increments the minor, otherwise
it increments the major.

```
~1.2.3  →  >=1.2.3 <1.3.0        ~1.2  →  >=1.2.0 <1.3.0
~0.2.3  →  >=0.2.3 <0.3.0        ~1    →  >=1.0.0 <2.0.0
~1.2.3-beta  →  >=1.2.3-beta <1.3.0
```

### Hyphen ranges

`A - B`, with the hyphen as its own whitespace-separated token. Both bounds need
at least a major component, and a comparator set that contains a bare `-` token
must be exactly the three tokens `A - B`.

The lower bound is `>=` A completed with zeros, keeping its prerelease. If B is
fully specified the upper bound is `<=B`; otherwise it is `<` B with its last
specified component incremented and everything to its right zeroed.

```
1.2.3 - 2.3.4  →  >=1.2.3 <=2.3.4
1.2 - 2.3      →  >=1.2.0 <2.4.0
1.2.3 - 2      →  >=1.2.3 <3.0.0
```

A range whose bounds cross (`2.0.0 - 1.0.0`, `>=2.0.0 <1.0.0`) is not an error;
it simply matches nothing.

### Unions

`||` splits the expression into comparator sets. Every side must hold at least
one comparator: `1.2.3 ||` is malformed. Only the whole expression may be empty
or blank, and that expression matches everything.

## The prerelease rule

A version **without** a prerelease satisfies a comparator set when it satisfies
every primitive comparator in that set.

A version **with** a prerelease satisfies a comparator set only when both hold:

1. it satisfies every primitive comparator in the set, and
2. at least one primitive comparator in that **same** set has a version that
   itself has a prerelease and whose `[major, minor, patch]` is equal to the
   candidate's.

So `1.5.0-beta` does not satisfy `>=1.0.0 <2.0.0` even though it lies inside the
interval, and `1.2.4-alpha` does not satisfy `^1.2.3-alpha` — but `1.2.3-beta`
does, and so does the ordinary release `1.9.0`.

## Errors

Raise `RangeError` (already defined in `src/semver.py`) for a malformed version
anywhere in `versions` and for a malformed range expression. `RangeError`
subclasses `ValueError`.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
