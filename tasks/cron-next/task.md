# cron-next

Implement `next_firings` in `src/cron.py`.

```python
def next_firings(expr: str, start: datetime, count: int) -> list[datetime]
```

Return the next `count` times a five-field cron expression fires, strictly after
`start`. All datetimes are naive and treated as UTC. Firing times always have
`second == 0` and `microsecond == 0`.

## Expression format

Five whitespace-separated fields:

```
minute  hour  day-of-month  month  day-of-week
0-59    0-23  1-31          1-12   0-7
```

Each field is a comma-separated list of terms. A term is one of:

| Term    | Meaning                                                        |
| ------- | -------------------------------------------------------------- |
| `*`     | every value in the field's range                                 |
| `N`     | the single value `N`                                             |
| `A-B`   | every value from `A` to `B` inclusive                            |
| `A-B/S` | every `S`-th value from `A` to `B` inclusive, starting at `A`    |
| `*/S`   | every `S`-th value across the whole range, starting at the low end |
| `N/S`   | every `S`-th value from `N` to the field's high end              |

In the month field, the names `JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC`
may be used in place of numbers. In the day-of-week field, the names
`SUN MON TUE WED THU FRI SAT` may be used. Names are case-insensitive and may
appear on either side of a range.

In the day-of-week field `0` and `7` both mean Sunday.

## Day matching

A field is **unrestricted** only when its text is exactly `*`. Anything else —
including `*/1` — is restricted.

A date matches when its month matches the month field and:

- both day-of-month and day-of-week are restricted → the date matches if
  **either** field matches;
- exactly one of them is restricted → only that field decides;
- neither is restricted → every day matches.

## Errors

Raise `CronError` (already defined in `src/cron.py`) when:

- the expression does not have exactly five fields;
- a term is malformed, or a value falls outside its field's range;
- a step is less than 1;
- a range has its low bound above its high bound;
- no firing exists within five years of `start`.

`count` may be `0`, in which case return an empty list.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
