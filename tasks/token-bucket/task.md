# token-bucket

Implement `decide` in `src/bucket.py`.

```python
def decide(config: dict, events: list[Event]) -> list[Decision]
```

Replay `events` through a per-key token bucket and return one `Decision` per
event, in the same order. `Event` and `Decision` are the `NamedTuple`s already
defined in `src/bucket.py`:

```python
class Event(NamedTuple):
    timestamp_ms: int
    key: str
    cost: int

class Decision(NamedTuple):
    allowed: bool
    remaining: int
    retry_after_ms: int
```

## Config

| Key                  | Meaning                                              |
| -------------------- | ---------------------------------------------------- |
| `capacity`           | bucket size in whole tokens — required                |
| `refill_tokens`      | tokens added per interval — required                  |
| `refill_interval_ms` | length of that interval, in milliseconds — required   |
| `initial_tokens`     | tokens a fresh bucket starts with — optional, default `capacity` |

Every value present is an `int`. The refill **rate** is the exact rational

```
refill_tokens / refill_interval_ms      tokens per millisecond
```

It is deliberately not a whole number of tokens per millisecond, and it must
never be rounded.

## Replay

Events arrive sorted by `timestamp_ms`. Several events may share a timestamp;
those are processed in the order given.

Each distinct `key` has its own independent bucket. A key's bucket is created at
the timestamp of that key's **first** event, holding `initial_tokens` tokens.
Time before a key's first event does not refill it.

For every event `(t, key, cost)`, in order:

**1. Refill.** If the bucket already existed, add `(t - last_t) * rate` tokens,
where `last_t` is the timestamp of the previous event for *this* key. Refill is
continuous — fractions of a token accrue and are carried forward exactly. The
result is then clamped to `capacity`: a bucket never holds more than `capacity`
tokens, however long it has idled.

**2. Decide.**

- If `cost > capacity` the request can never be served by this bucket. `allowed`
  is `False` and `retry_after_ms` is `-1`. No tokens are taken.
- Otherwise, if the bucket holds **at least** `cost` tokens, `cost` tokens are
  removed, `allowed` is `True` and `retry_after_ms` is `0`.
- Otherwise the request is denied. **No tokens are taken** — a denied request
  never partially drains the bucket. `retry_after_ms` is the smallest whole
  number of milliseconds `d` such that, if no further event touched this key,
  the bucket would hold at least `cost` tokens at `t + d`. The exact wait is
  usually fractional, so this **rounds up** to the next whole millisecond; when
  the exact wait happens to be a whole number of milliseconds, that number is
  used as-is.

**3. Report.** `remaining` is the bucket's token count *after* the decision,
floored to a whole token — 4.99 tokens report as `4`. It is reported on denied
decisions too, where it is simply the refilled count.

`last_t` advances to `t` on every event for that key, allowed or denied.

## Exact arithmetic is part of the contract

A third of a token is `1/3`, not `0.3333333333333333`. Timelines run to
hundreds of events and the tests check decisions that sit exactly on a token
boundary, so accumulated floating-point error changes answers. Use
`fractions.Fraction` or integer arithmetic; `float` will not survive the tests.

## Errors

Raise `ConfigError` (already defined in `src/bucket.py`) when:

- `capacity`, `refill_tokens` or `refill_interval_ms` is missing;
- `capacity` is less than 1;
- `refill_tokens` is less than 1;
- `refill_interval_ms` is less than 1;
- `initial_tokens` is present and is negative or greater than `capacity`;
- any event has a negative `cost`;
- the events are not sorted — some event's timestamp is strictly less than its
  predecessor's.

`decide` raises rather than returning a partial list. Timestamps may be any
integers, negative ones included, as long as they never decrease. An empty event
list returns an empty list.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
