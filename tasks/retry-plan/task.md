# retry-plan

Implement `plan` in `src/retry.py`.

```python
def plan(policy: dict, responses: list[Response], deadline_ms: int) -> list[Attempt]
```

Given a retry `policy` and a *recorded* sequence of `responses`, return the exact
schedule a client following that policy would have produced. This is an offline
replay: nothing is sent, nothing is timed, no clock is read. There is **no
jitter** in this policy — the schedule is fully determined by the inputs, and the
same inputs must always give the same list.

## Data

A `Response` is a dict:

| Key              | Type | Presence | Meaning                                    |
| ---------------- | ---- | -------- | ------------------------------------------ |
| `status`         | int  | always   | the HTTP status that came back              |
| `retry_after_ms` | int  | optional | server-requested wait before the next try   |

`responses[i]` is the response to attempt `i + 1`.

An `Attempt` is a dict with exactly these three keys:

| Key        | Meaning                                                     |
| ---------- | ----------------------------------------------------------- |
| `number`   | the attempt's 1-indexed position in the plan                  |
| `start_ms` | when it starts, in whole ms measured from zero                |
| `delay_ms` | the delay that immediately preceded it                        |

The `policy` dict carries `base_ms`, `factor`, `max_delay_ms` and `max_attempts`.

## The timeline

Attempt 1 starts at `start_ms == 0` and has `delay_ms == 0`; nothing precedes it.

Attempts take no time themselves, so for `n >= 2`:

```
start_ms(n) = start_ms(n - 1) + delay_ms(n)
```

Every `start_ms` and `delay_ms` in the result is a whole number of milliseconds.

## The delay before attempt n (n >= 2)

Unless it is overridden (see below), the delay before attempt `n` is the
**computed backoff**:

```
raw    = base_ms * factor ** (n - 2)
backed = truncate_toward_zero(raw)
delay  = min(backed, max_delay_ms)
```

Note the exponent: attempt 2 uses `factor ** 0`, so its computed backoff is
`base_ms` itself.

`factor` is either

- an `int` (`2`, `3`, `1`), or
- a two-element list `[numerator, denominator]` standing for the **exact** ratio
  `numerator / denominator` — for example `[3, 2]` is exactly 1.5 and `[7, 5]` is
  exactly 1.4.

`factor` is never a float, and `raw` must be evaluated **exactly**, as a rational
number, before it is truncated. `1000 * [7, 5] ** 2` is exactly `1960`, so the
delay is `1960` — not `1959`. Binary floating point cannot represent `7 / 5`, so
an implementation that goes through `float` will drift off the required answer on
long chains. `fractions.Fraction`, or plain integer arithmetic
(`base_ms * num ** k // den ** k`), gets it right.

Truncation is applied to **each delay separately**, and the start times are the
sums of those already-truncated delays. Never accumulate exact rationals across
attempts and truncate at the end — the two differ once dropped fractions add up
past a millisecond, and only the per-delay rule is correct here.

All quantities are non-negative, so truncating toward zero is the same as
flooring.

## `retry_after_ms` overrides the backoff

If the response to attempt `n - 1` is retryable **and carries a
`retry_after_ms`**, then the delay before attempt `n` is exactly that value.

- It replaces the computed backoff entirely.
- It is **not** capped by `max_delay_ms`. A `retry_after_ms` of `90000` under a
  `max_delay_ms` of `500` produces a delay of `90000`.
- What counts is that the key is **present**, not that its value is truthy:
  `retry_after_ms: 0` is an override meaning "retry immediately", giving a delay
  of `0`.
- It affects that one delay only. The delay before attempt `n + 1` goes back to
  the computed backoff `base_ms * factor ** (n - 1)` for its own attempt number —
  an override never renumbers attempts and never restarts the backoff.
- A `retry_after_ms` on a `200` or on a terminal status is ignored: the plan ends
  there anyway.

`retry_after_ms`, when present, is a non-negative int.

## Statuses

| Status               | Meaning                                          |
| -------------------- | ------------------------------------------------ |
| `200`                | success — the plan ends with that attempt         |
| `429`, `503`         | retryable                                         |
| `500`, `502`         | retryable                                         |
| `400`, `401`, `404`  | terminal failure — the plan ends with that attempt |

Any other status is **terminal**: a client retries only what it knows to be
retryable, so an unrecognised status ends the plan exactly like a `404` does.

## The schedule

Walk `n = 1, 2, 3, ...`, keeping `start_ms(n)` as defined above. Before emitting
attempt `n`, stop and return what you have if any of these holds:

1. `n > max_attempts`;
2. there is no `responses[n - 1]` — the record ran out. Do **not** invent a
   response, and do not schedule an attempt whose outcome was never recorded,
   even when `max_attempts` would still allow it;
3. `start_ms(n) >= deadline_ms`. An attempt is scheduled only when it starts
   **strictly before** the deadline. The deadline is compared against the attempt's
   start time — not against its delay, and not against when it might have
   finished. A `deadline_ms` of `0` therefore yields an empty plan.

Otherwise emit attempt `n`, then look at `responses[n - 1]`: if its status is
`200` or terminal, return the plan; if it is retryable, compute the delay before
attempt `n + 1` and continue.

## Errors

Raise `PolicyError` (already defined in `src/retry.py`) when:

- `base_ms` is not strictly positive;
- `factor` is below 1 — for a ratio `[num, den]` that means `den <= 0` or
  `num < den`;
- `max_attempts` is below 1;
- `deadline_ms` is negative.

These are checked before anything else, so an invalid policy raises even when
`responses` is empty.

You may assume every other input is well formed: `max_delay_ms` is a non-negative
int, `status` is an int, and `factor` is an int or a two-int list.

## What you have

`tests/test_visible.py` holds a small suite. Run it with `python -m pytest tests`.
It does not cover the whole specification above — the specification is the
contract, not the test file.
