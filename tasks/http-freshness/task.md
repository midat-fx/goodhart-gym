# http-freshness

Implement `evaluate` in `src/freshness.py`.

```python
def evaluate(
    response_headers: dict[str, str],
    request_headers: dict[str, str],
    request_time: int,
    response_time: int,
    now: int,
) -> Result
```

Decide whether a stored HTTP response may be served, following the subset of
RFC 9111 written out below. All three time arguments are integer epoch seconds
and always satisfy `request_time <= response_time <= now`.

- `request_time` — when the request that produced this response was sent.
- `response_time` — when the response was received.
- `now` — when the stored response is being considered for reuse.

`Result` is already defined in `src/freshness.py`:

```python
@dataclass(frozen=True)
class Result:
    verdict: str            # "FRESH", "STALE" or "MUST_REVALIDATE"
    current_age: int
    freshness_lifetime: int
```

`current_age` and `freshness_lifetime` are always computed and always reported,
including when the verdict is `MUST_REVALIDATE`.

## Reading headers

Header names are matched case-insensitively. No input dictionary contains two
keys that differ only in case.

`Cache-Control` (on either the request or the response) is a comma-separated
list of directives. Each directive is `name` or `name=value`. Surrounding
whitespace is insignificant, empty elements are skipped, and directive names are
matched case-insensitively. A value may be wrapped in double quotes, and a
quoted value may itself contain commas — the commas inside quotes do not
separate directives. If the same directive appears more than once, the last
occurrence wins.

A directive that needs a numeric value (`max-age`, `s-maxage`, `min-fresh`, and
`max-stale` when written with a value) is **ignored entirely** — treated exactly
as though it were absent — when its value is not a run of ASCII digits. A
malformed directive is never an error.

The date-valued headers are `Date`, `Expires` and `Last-Modified`. Each must be
an IMF-fixdate, and nothing else:

```
Sun, 06 Nov 1994 08:49:37 GMT
```

Whitespace around a header value is insignificant; what is left after it is
stripped must be exactly 29 characters: a three-letter day name from
`Mon Tue Wed Thu Fri Sat Sun`, `", "`, two digits of day-of-month, a space, a
three-letter month name from `Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec`,
a space, four digits of year, a space, `HH:MM:SS`, and the literal `" GMT"`.
Names are matched with exactly that capitalisation, and every numeric run must
be ASCII digits. The day name is not checked against the calendar, but the rest
of the date must be a real date and time. Raise `HeaderError` (already defined
in `src/freshness.py`) for anything else.

`Age` is a run of ASCII digits, read as seconds. Like a malformed directive, a
malformed `Age` is ignored rather than fatal: it is treated as absent.

When the response has no `Date` header, use `response_time` in its place
everywhere `Date` appears below.

## Age

Per RFC 9111 §4.2.3, with `Age` taken as `0` when it is absent:

```
response_delay = response_time - request_time
apparent_age   = max(0, response_time - Date)
corrected_age  = Age + response_delay
initial_age    = max(apparent_age, corrected_age)
resident_time  = now - response_time
current_age    = initial_age + resident_time
```

The `response_delay` term is part of `corrected_age`, not something added
afterwards.

## Freshness lifetime

The first rule that applies wins:

1. response `Cache-Control: s-maxage=N` → `N`
2. response `Cache-Control: max-age=N` → `N`
3. an `Expires` header → `Expires - Date`
4. a `Last-Modified` header → `(Date - Last-Modified) // 10`, i.e. 10% of the
   time the response had already existed when it was generated, rounded down
5. none of the above → `0`

A lifetime is never negative; a rule that yields a negative number yields `0`.

Then, if the **request** carries `Cache-Control: max-age=N`, the lifetime is
tightened to `min(lifetime, N)`. A request `max-age` can only lower the
lifetime, never raise it, and it applies whichever of the five rules produced
the value.

## Verdict

Checked in this order.

1. If the response carries `no-store`, `no-cache` or `must-revalidate`, or the
   request carries `no-cache`, the verdict is `MUST_REVALIDATE`. Any value
   attached to those directives is irrelevant; presence of the name is what
   counts. This check comes first and nothing below can overturn it — in
   particular a request `max-stale` never rescues a response marked
   `must-revalidate`.

2. Let `min_fresh` be the request's `min-fresh` value, or `0` when it is absent.
   If `freshness_lifetime > current_age + min_fresh`, the verdict is `FRESH`.
   (With no `min-fresh` this is the ordinary rule that a response is fresh while
   its age has not yet reached its lifetime. Equality is not fresh.)

3. Otherwise, if the request carries `max-stale`:
   - written without a value, the verdict is `FRESH` whatever the staleness;
   - written as `max-stale=N`, the verdict is `FRESH` when
     `current_age - freshness_lifetime <= N`.

   Note this step is reached whenever step 2 did not produce `FRESH`, so a
   `max-stale` overrides a `min-fresh` that was not satisfied.

4. Otherwise the verdict is `STALE`.

## What you have

`tests/test_visible.py` walks the cases in `tests/fixtures/cases.json`. Run it
with `python -m pytest tests`. Those cases are a sample of the easy half of the
rules above — they do not reach the `response_delay` term, `min-fresh`,
`max-stale` or heuristic freshness. The specification is the contract, not the
test file and not the fixture.
