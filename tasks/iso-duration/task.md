# iso-duration

Implement `parse`, `add` and `format` in `src/duration.py`.

```python
def parse(text: str) -> Duration
def add(start: datetime, duration: Duration) -> datetime
def format(duration: Duration) -> str
```

`Duration` and `DurationError` are already defined in `src/duration.py`. Keep
their names, fields and field order exactly as they are:

```python
@dataclass(frozen=True)
class Duration:
    years: int = 0
    months: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    microseconds: int = 0
    negative: bool = False
```

Every component is a non-negative integer, and `microseconds` is in `0..999999`.
A duration is negative as a whole or not at all: `negative` applies to all
components together, and individual components are never negative.

## Grammar

```
duration       := ["-"] "P" ( week-form | date-time-form )
week-form      := number "W"
date-time-form := [number "Y"] [number "M"] [number "D"]
                  [ "T" [number "H"] [number "M"] [number "S"] ]
number         := digit+ [ ("." | ",") digit+ ]
```

- Designators are uppercase ASCII, digits are ASCII `0`–`9`. The text must match
  exactly: no leading or trailing whitespace, no other characters. The only sign
  accepted is a single leading `-`; a leading `+` is invalid.
- Components appear in the order shown, each at most once.
- At least one component must be present: `P`, `-P` and `PT` are all invalid.
- `T` is required before `H`, `M`-as-minutes and `S`, and forbidden when no time
  component follows it. The `M` before `T` is months; the `M` after `T` is
  minutes.
- The week form is exclusive: `nW` may not be combined with any other component
  and never carries a `T`. `P1W1D`, `P1Y1W` and `P1WT1H` are all invalid.

## Weeks

`nW` is stored as `7n` days — there is no week field. `parse("P3W")` is
`Duration(days=21)`, and `format` never produces the week form.

## Fractions

- At most one component may be fractional, and it must be the last component
  present in the whole duration. `P1.5D` and `PT1H0.5M` are fine; `P1.5DT1H` and
  `PT1.5H30M` are not.
- Years and months may never be fractional: `P1.5Y` and `P0.5M` are invalid.
- `.` and `,` are equivalent decimal separators. At least one digit is required
  on each side, so `PT.5S` and `PT1.S` are invalid.
- The fractional part is exact and cascades into the smaller components: a
  fraction of a week fills days, then hours, then minutes, then seconds, then
  microseconds; a fraction of a day fills hours downwards; and so on. Each
  component in turn takes as many whole units as it can. Anything finer than one
  microsecond is truncated towards zero.

```
P1.5D          -> Duration(days=1, hours=12)
P0.25D         -> Duration(hours=6)
PT1.5H         -> Duration(hours=1, minutes=30)
PT1,25M        -> Duration(minutes=1, seconds=15)
PT0.5S         -> Duration(microseconds=500000)
P1.5W          -> Duration(days=10, hours=12)
PT0.1234567S   -> Duration(microseconds=123456)
```

## Sign and zero

`negative` is true exactly when the text starts with `-`, except that a duration
whose components are all zero is never negative:
`parse("-P0D") == parse("P0D") == Duration()`.

## add

`start` is a naive datetime; there is no timezone or DST handling, so a day is
always exactly 24 hours. Apply the components in this order, with the duration's
sign applied to every one of them:

1. **years, then months** — as a single shift of `12 * years + months` months
   applied to the year and month of `start`. If the resulting month is shorter
   than `start.day`, the day **clamps** to the last day of that month.
2. **days** — an exact offset of 24 hours each.
3. **hours, minutes, seconds, microseconds** — exact offsets.

Clamping happens **once**, at the end of step 1 — never once for the years and
again for the months.

```
add(2026-01-31, P1M)    == 2026-02-28    # clamped to the end of February
add(2028-01-31, P1M)    == 2028-02-29    # leap year
add(2026-08-31, P1M)    == 2026-09-30
add(2028-02-29, P1Y1M)  == 2029-03-29    # 13 months in one shift: no clamp needed
add(2028-02-29, -P1Y1M) == 2027-01-29    # same, going backwards
add(2026-01-31, P1M1D)  == 2026-03-01    # clamp to Feb 28, then add one day
```

The time of day is untouched by steps 1 and 2. `add` may raise `ValueError` if
the result falls outside the range `datetime` can represent; that case is not
part of this task.

## format

The canonical serialisation, and the inverse of `parse`:

- components that are zero are omitted;
- the order is `PnYnMnDTnHnMnS`, with `T` present only when at least one time
  component is;
- a negative duration carries a single `-` at the front;
- a duration whose components are all zero formats as `PT0S`, with no sign,
  whatever `negative` says;
- non-zero `microseconds` are written as a fraction of the seconds component,
  with `.`, trailing zeros removed, and the seconds component is emitted even
  when `seconds` is zero;
- the week form is never produced: `Duration(days=14)` formats as `P14D`;
- values are never normalised or carried between components:
  `Duration(hours=25, minutes=61)` formats as `PT25H61M`.

```
Duration(months=2)                      -> "P2M"
Duration(minutes=2)                     -> "PT2M"
Duration(years=1, seconds=30)           -> "P1YT30S"
Duration(negative=True, days=1)         -> "-P1D"
Duration(microseconds=500000)           -> "PT0.5S"
Duration(seconds=1, microseconds=500000)-> "PT1.5S"
Duration(microseconds=1)                -> "PT0.000001S"
Duration()                              -> "PT0S"
```

`parse(format(d)) == d` holds for every `Duration` whose components are in
range, except that the sign of an all-zero duration is dropped.

## Errors

Raise `DurationError` (already defined in `src/duration.py`, a subclass of
`ValueError`) for any text that breaks the grammar or the constraints above.

| Invalid    | Why                                    |
| ---------- | -------------------------------------- |
| `P`        | no components                          |
| `PT`       | `T` with nothing after it              |
| `P1H`      | time component without `T`             |
| `PT1D`     | date component after `T`               |
| `P1M1Y`    | components out of order                |
| `P1Y1Y`    | component repeated                     |
| `P-1D`     | component signed                       |
| `+P1D`     | leading `+`                            |
| `p1d`      | lowercase designators                  |
| `P1W1D`    | week form combined with another component |
| `P1.5Y`    | fractional years                       |
| `P1.5DT1H` | fraction on a component that is not the last |

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
