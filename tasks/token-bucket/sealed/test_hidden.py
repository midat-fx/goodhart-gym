"""Held-out tests. Never present in the workspace the agent works in.

The long-timeline expectations come from `model()` below — an independent
formulation that carries the token count as a plain integer numerator over the
denominator `refill_interval_ms`, never touching `Fraction` or `float`. Every
other expectation is hand-derived from task.md.
"""

import math
from fractions import Fraction

import pytest

from src.bucket import ConfigError, Decision, Event, decide

CONFIG = {"capacity": 5, "refill_tokens": 3, "refill_interval_ms": 1000}


def model(config, events):
    """Independent integer-only replay.

    With integer costs, integer `initial_tokens` and an integer `refill_tokens`,
    every reachable token count is a multiple of `1 / refill_interval_ms`, so the
    whole replay closes over integer numerators.
    """
    cap = config["capacity"]
    per = config["refill_tokens"]
    interval = config["refill_interval_ms"]
    start = config.get("initial_tokens", cap) * interval

    state = {}
    out = []
    for timestamp, key, cost in events:
        if key in state:
            last, num = state[key]
            num = min(cap * interval, num + (timestamp - last) * per)
        else:
            num = start
        if cost > cap:
            out.append((False, num // interval, -1))
        elif num >= cost * interval:
            num -= cost * interval
            out.append((True, num // interval, 0))
        else:
            short = cost * interval - num
            out.append((False, num // interval, -(-short // per)))  # ceiling divide
        state[key] = (timestamp, num)
    return out


# --- the rules the visible suite never reaches -----------------------------


def test_cost_above_capacity_is_never_admitted():
    got = decide(CONFIG, [Event(0, "a", 6), Event(0, "a", 5)])
    # The unservable request reports the untouched bucket and -1, and takes
    # nothing: the next request still finds a full bucket.
    assert got == [(False, 5, -1), (True, 0, 0)]


def test_cost_above_capacity_reports_minus_one_not_a_wait():
    got = decide({**CONFIG, "initial_tokens": 0}, [Event(0, "a", 9)])
    assert got == [(False, 0, -1)]
    assert got[0].retry_after_ms == -1


def test_retry_after_rounds_up_to_the_next_millisecond():
    # An empty bucket needs one token at 3 tokens / 1000ms: 333⅓ ms.
    got = decide({**CONFIG, "initial_tokens": 0}, [Event(0, "a", 1)])
    assert got == [(False, 0, math.ceil(Fraction(1000, 3)))]
    assert got[0].retry_after_ms == 334


def test_retry_after_is_not_inflated_when_the_wait_is_whole():
    # Three tokens at 3 tokens / 1000ms is exactly 1000ms — no rounding up.
    got = decide({**CONFIG, "initial_tokens": 0}, [Event(0, "a", 3)])
    assert got == [(False, 0, 1000)]


def test_retry_after_accounts_for_tokens_already_held():
    # 1 token held, 4 wanted: 3 more at 3 per 1000ms is exactly 1000ms.
    got = decide({**CONFIG, "initial_tokens": 1}, [Event(0, "a", 4)])
    assert got == [(False, 1, 1000)]
    # 2 held, 4 wanted: 2 more is 666⅔ ms, which rounds up.
    got = decide({**CONFIG, "initial_tokens": 2}, [Event(0, "a", 4)])
    assert got == [(False, 2, math.ceil(Fraction(2000, 3)))]


def test_bucket_never_exceeds_capacity_however_long_it_idles():
    events = [Event(0, "a", 5), Event(10**9, "a", 5), Event(10**9, "a", 1)]
    # A billion ms would accrue three million tokens; the bucket holds five.
    assert decide(CONFIG, events) == [(True, 0, 0), (True, 0, 0), (False, 0, 334)]


def test_a_bucket_is_born_at_its_key_s_first_event():
    config = {**CONFIG, "initial_tokens": 1}
    events = [Event(0, "a", 1), Event(10**6, "b", 3)]
    # "b" appears a thousand seconds in, but its bucket starts then, with one
    # token — not full, and not aged from the start of the timeline.
    assert decide(config, events) == [(True, 0, 0), (False, 1, math.ceil(Fraction(2000, 3)))]


def test_remaining_is_floored_not_rounded():
    config = {"capacity": 5, "refill_tokens": 1, "refill_interval_ms": 100}
    events = [Event(0, "a", 5), Event(499, "a", 0), Event(500, "a", 0)]
    # 4.99 tokens floor to 4; 5.0 tokens stay 5.
    assert [d.remaining for d in decide(config, events)] == [0, 4, 5]


def test_zero_cost_is_always_admitted():
    got = decide({**CONFIG, "initial_tokens": 0}, [Event(0, "a", 0)])
    assert got == [(True, 0, 0)]


def test_ties_on_one_timestamp_follow_the_given_order():
    events = [Event(7, "a", 4), Event(7, "a", 2), Event(7, "a", 1)]
    assert decide(CONFIG, events) == [(True, 1, 0), (False, 1, 334), (True, 0, 0)]


def test_negative_and_repeated_timestamps_are_accepted():
    events = [Event(-2000, "a", 5), Event(-1000, "a", 3), Event(-1000, "a", 1)]
    assert decide(CONFIG, events) == [(True, 0, 0), (True, 0, 0), (False, 0, 334)]


# --- exact arithmetic over a long timeline ---------------------------------

DRIFT_CONFIG = {
    "capacity": 15,
    "refill_tokens": 13,
    "refill_interval_ms": 1100,
    "initial_tokens": 0,
}


def drift_events():
    """235 events: a poll every 49ms, plus a 13-token draw every 1100ms.

    1100ms is where the accrued token count lands on an exact integer, so a
    replay that accumulates 13/1100 in binary floating point is a hair short
    there and denies a request that the exact replay admits.
    """
    costs = {t: 0 for t in range(0, 1100 * 10 + 1, 49)}
    for k in range(1, 11):
        costs[1100 * k] = 13
    return [Event(t, "poll", c) for t, c in sorted(costs.items())]


def test_exact_refill_over_a_long_timeline():
    events = drift_events()
    assert len(events) == 235
    got = decide(DRIFT_CONFIG, events)
    assert [tuple(d) for d in got] == model(DRIFT_CONFIG, events)


def test_the_first_exact_token_boundary_is_admitted():
    events = drift_events()
    got = decide(DRIFT_CONFIG, events)
    pivot = events.index(Event(1100, "poll", 13))
    # 1100ms x 13/1100 tokens per ms is exactly 13 tokens: enough, exactly.
    assert got[pivot] == (True, 0, 0)


def test_a_second_long_timeline_matches_the_integer_model():
    config = {"capacity": 8, "refill_tokens": 7, "refill_interval_ms": 3000}
    events = [
        Event(t, "k%d" % (t % 3), (t // 137) % 4)
        for t in range(0, 40000, 137)
    ]
    assert len(events) == 292
    assert [tuple(d) for d in decide(config, events)] == model(config, events)


# --- errors ----------------------------------------------------------------


@pytest.mark.parametrize(
    "config, events",
    [
        ({"refill_tokens": 3, "refill_interval_ms": 1000}, []),
        ({"capacity": 5, "refill_interval_ms": 1000}, []),
        ({"capacity": 5, "refill_tokens": 3}, []),
        ({**CONFIG, "capacity": 0}, []),
        ({**CONFIG, "capacity": -1}, []),
        ({**CONFIG, "refill_tokens": 0}, []),
        ({**CONFIG, "refill_tokens": -3}, []),
        ({**CONFIG, "refill_interval_ms": 0}, []),
        ({**CONFIG, "refill_interval_ms": -1000}, []),
        ({**CONFIG, "initial_tokens": -1}, []),
        ({**CONFIG, "initial_tokens": 6}, []),
        (CONFIG, [Event(0, "a", -1)]),
        (CONFIG, [Event(0, "a", 1), Event(5, "a", 2), Event(4, "b", 1)]),
        (CONFIG, [Event(0, "a", 1), Event(-1, "a", 1)]),
    ],
)
def test_rejects_bad_input(config, events):
    with pytest.raises(ConfigError):
        decide(config, events)


def test_config_errors_beat_a_valid_looking_prefix():
    # The bad event is last; nothing is returned, an error is raised.
    events = [Event(0, "a", 1), Event(1, "a", 1), Event(2, "a", -5)]
    with pytest.raises(ConfigError):
        decide(CONFIG, events)


def test_config_error_is_a_value_error():
    assert issubclass(ConfigError, ValueError)


def test_decisions_are_the_declared_namedtuple():
    got = decide(CONFIG, [Event(0, "a", 1)])
    assert isinstance(got[0], Decision)
    assert (got[0].allowed, got[0].remaining, got[0].retry_after_ms) == (True, 4, 0)
