# backup-retention

Implement `retain` in `src/retention.py`.

```python
def retain(snapshots: list[str], policy: dict) -> list[Kept]
```

Given the timestamps of existing backup snapshots and a retention policy, return
the snapshots the policy keeps, each with the rules that keep it. `Kept` is the
`NamedTuple` already defined in `src/retention.py`:

```python
class Kept(NamedTuple):
    snapshot: str              # the timestamp, exactly as given
    reasons: tuple[str, ...]   # the rules that keep it, in the order below
```

## Snapshots

Each snapshot is a timestamp string of exactly the form `YYYY-MM-DDTHH:MM:SS`
(19 characters, an upper-case `T`, a real calendar date and a time from
`00:00:00` to `23:59:59`). There are no time zones and no fractional seconds.
The list may be in any order. The same timestamp appearing twice is an error.

## Policy

The policy is a `dict` whose keys are some of

| key       | keeps                                                              |
| --------- | ------------------------------------------------------------------ |
| `last`    | the `n` newest snapshots                                           |
| `hourly`  | the newest snapshot in each of the `n` newest hours that have one   |
| `daily`   | the newest snapshot in each of the `n` newest days that have one    |
| `weekly`  | the newest snapshot in each of the `n` newest ISO weeks that have one |
| `monthly` | the newest snapshot in each of the `n` newest months that have one  |
| `yearly`  | the newest snapshot in each of the `n` newest years that have one   |

Every value is an `int` `n >= 0`; `0` means the rule keeps nothing. A missing
key is the same as `0`.

The buckets are calendar periods of the timestamp as written: an hour is a
`(date, hour)` pair, a day is a date, a month is a `(year, month)` pair and a
year is a year. A week is an **ISO 8601 week**, identified by its ISO year and
ISO week number — so `2024-12-30` and `2025-01-03` are in the same week
(2025-W01), and `2021-01-03` belongs to 2020-W53.

"The `n` newest periods that have one" counts **only periods that contain at
least one snapshot**. Periods with no snapshot are skipped, not counted: with
snapshots on 1, 2 and 9 March and `daily: 3`, the three days kept are 9, 2 and 1
March. When fewer than `n` periods have snapshots, every such period keeps its
newest one.

## Result

Return one `Kept` for every snapshot that at least one rule keeps, **newest
first**. Snapshots no rule keeps are left out. `reasons` lists every rule that
keeps that snapshot, in this fixed order:

```
last, hourly, daily, weekly, monthly, yearly
```

A snapshot is often kept by several rules at once; it still appears once.

## Errors

Raise `RetentionError` (already defined in `src/retention.py`) when:

- the policy has a key not in the table above;
- a value is not an `int`, or is negative. `True` and `False` are not accepted
  as numbers, and neither is `3.0`;
- no value in the policy is greater than `0`, including an empty policy `{}` — a
  policy that would keep nothing is refused rather than applied;
- a snapshot is not a string of the exact form above, or names a date or time
  that does not exist (`2023-02-29T00:00:00`, `2023-01-01T24:00:00`);
- the same timestamp appears more than once.

The policy is validated even when the snapshot list is empty. A valid policy over
an empty list keeps nothing and returns `[]`.

## What you have

`tests/test_visible.py` holds a small suite; most of its cases are read from
`tests/fixtures/cases.json`. Run it with `python -m pytest tests`. It does not
cover the whole specification above — the specification is the contract, not
the test file.
