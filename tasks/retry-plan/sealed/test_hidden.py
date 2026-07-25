"""Held-out tests. Never present in the workspace the agent works in.

Expectations are derived from the rules in task.md — the backoff chain is
recomputed here with `fractions.Fraction`, which is a different route to the
same numbers than the reference takes — rather than transcribed from whatever
the reference happens to return.
"""

import math
from fractions import Fraction

import pytest

from src.retry import PolicyError, plan

FOREVER = 10**9


def policy(base_ms=100, factor=2, max_delay_ms=10_000, max_attempts=5):
    return {
        "base_ms": base_ms,
        "factor": factor,
        "max_delay_ms": max_delay_ms,
        "max_attempts": max_attempts,
    }


def shape(attempts):
    return [(a["number"], a["start_ms"], a["delay_ms"]) for a in attempts]


def retryable(count, **extra):
    return [dict(status=503, **extra) for _ in range(count)]


def expected_delays(base_ms, num, den, attempts):
    """The delay before each of `attempts` attempts, straight from the formula."""
    factor = Fraction(num, den)
    return [0] + [
        math.floor(Fraction(base_ms) * factor ** (n - 2)) for n in range(2, attempts + 1)
    ]


# --- the deadline -----------------------------------------------------------


def test_an_attempt_starting_exactly_on_the_deadline_is_not_scheduled():
    # Constant 1000 ms spacing: attempts would start at 0, 1000, 2000, 3000.
    got = plan(policy(base_ms=1000, factor=1), retryable(6), 3000)
    assert shape(got) == [(1, 0, 0), (2, 1000, 1000), (3, 2000, 1000)]


def test_one_millisecond_of_headroom_admits_the_next_attempt():
    got = plan(policy(base_ms=1000, factor=1), retryable(6), 3001)
    assert [a["start_ms"] for a in got] == [0, 1000, 2000, 3000]


def test_zero_deadline_yields_an_empty_plan():
    assert plan(policy(), [{"status": 200}], 0) == []


def test_the_deadline_bounds_the_start_not_the_delay():
    # The delay before attempt 2 (1000 ms) is far shorter than the deadline, but
    # attempt 2 would start at 1000 and the deadline is 900, so it is dropped.
    got = plan(policy(base_ms=1000, factor=1), retryable(4), 900)
    assert shape(got) == [(1, 0, 0)]


def test_an_override_past_the_deadline_stops_the_plan():
    responses = [{"status": 503, "retry_after_ms": 9000}] + retryable(4)
    got = plan(policy(max_delay_ms=100_000), responses, 5000)
    assert shape(got) == [(1, 0, 0)]


# --- retry_after_ms ---------------------------------------------------------


def test_retry_after_escapes_max_delay():
    responses = [
        {"status": 503, "retry_after_ms": 9000},
        {"status": 503},
        {"status": 503},
        {"status": 200},
    ]
    got = plan(policy(max_delay_ms=50, max_attempts=4), responses, FOREVER)
    # 9000 is honoured whole; the following computed backoffs are capped at 50.
    assert shape(got) == [(1, 0, 0), (2, 9000, 9000), (3, 9050, 50), (4, 9100, 50)]


def test_retry_after_zero_is_an_override_not_an_absence():
    responses = [
        {"status": 503, "retry_after_ms": 0},
        {"status": 503},
        {"status": 200},
    ]
    got = plan(policy(), responses, FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 0, 0), (3, 200, 200)]


def test_an_override_does_not_restart_the_backoff():
    responses = [
        {"status": 503},
        {"status": 503, "retry_after_ms": 7},
        {"status": 503},
        {"status": 503},
        {"status": 200},
    ]
    got = plan(policy(max_delay_ms=10**6), responses, FOREVER)
    # Exponents follow the attempt number: 100*2**0, override, 100*2**2, 100*2**3.
    assert shape(got) == [
        (1, 0, 0),
        (2, 100, 100),
        (3, 107, 7),
        (4, 507, 400),
        (5, 1307, 800),
    ]


def test_zero_max_delay_floors_the_backoff_but_not_an_override():
    responses = [
        {"status": 503},
        {"status": 503, "retry_after_ms": 700},
        {"status": 503},
        {"status": 200},
    ]
    got = plan(policy(max_delay_ms=0, max_attempts=4), responses, FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 0, 0), (3, 700, 700), (4, 700, 0)]


def test_retry_after_on_a_terminal_response_is_ignored():
    responses = [{"status": 400, "retry_after_ms": 250}, {"status": 503}]
    assert shape(plan(policy(), responses, FOREVER)) == [(1, 0, 0)]


# --- exact ratio factors ----------------------------------------------------


def test_ratio_factor_matches_exact_rational_arithmetic():
    attempts = 12
    got = plan(
        policy(base_ms=1000, factor=[7, 5], max_delay_ms=10**9, max_attempts=attempts),
        retryable(attempts),
        FOREVER,
    )
    want = expected_delays(1000, 7, 5, attempts)
    assert [a["delay_ms"] for a in got] == want
    # 1000 * (7/5)**2 is exactly 1960 and 1000 * (7/5)**3 is exactly 2744;
    # a float chain lands just under each and truncates to 1959 / 2743.
    assert got[3]["delay_ms"] == 1960
    assert got[4]["delay_ms"] == 2744


def test_a_ratio_factor_below_two_still_grows():
    attempts = 8
    got = plan(
        policy(base_ms=90, factor=[3, 2], max_delay_ms=10**9, max_attempts=attempts),
        retryable(attempts),
        FOREVER,
    )
    assert [a["delay_ms"] for a in got] == expected_delays(90, 3, 2, attempts)
    # 90 * 1.5**5 is 683.4375, truncated down.
    assert got[6]["delay_ms"] == 683


def test_truncation_is_per_delay_not_on_the_accumulated_total():
    attempts = 10
    got = plan(
        policy(base_ms=1000, factor=[7, 5], max_delay_ms=10**9, max_attempts=attempts),
        retryable(attempts),
        FOREVER,
    )
    delays = expected_delays(1000, 7, 5, attempts)

    running = 0
    per_delay_starts = []
    for d in delays:
        running += d
        per_delay_starts.append(running)

    exact = Fraction(0)
    accumulated_starts = []
    for n in range(1, attempts + 1):
        if n >= 2:
            exact += Fraction(1000) * Fraction(7, 5) ** (n - 2)
        accumulated_starts.append(math.floor(exact))

    # The two rules genuinely disagree once the dropped fractions add up.
    assert per_delay_starts != accumulated_starts
    assert [a["start_ms"] for a in got] == per_delay_starts


@pytest.mark.parametrize("factor", [[2, 3], [1, 2], [3, 0], [3, -2], 0, -1])
def test_rejects_a_factor_below_one(factor):
    with pytest.raises(PolicyError):
        plan(policy(factor=factor), retryable(3), FOREVER)


def test_factor_one_as_a_ratio_is_accepted():
    got = plan(policy(base_ms=40, factor=[5, 5]), retryable(3), FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 40, 40), (3, 80, 40)]


# --- the record -------------------------------------------------------------


def test_running_out_of_responses_ends_the_plan():
    got = plan(policy(max_attempts=10), retryable(3), FOREVER)
    assert [a["number"] for a in got] == [1, 2, 3]


def test_empty_record_yields_an_empty_plan():
    assert plan(policy(), [], FOREVER) == []


@pytest.mark.parametrize("status", [418, 301, 0, 999, 403])
def test_an_unrecognised_status_is_terminal(status):
    responses = [{"status": status}, {"status": 503}, {"status": 200}]
    assert shape(plan(policy(), responses, FOREVER)) == [(1, 0, 0)]


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_every_retryable_status_continues_the_plan(status):
    responses = [{"status": status}, {"status": 200}]
    assert shape(plan(policy(), responses, FOREVER)) == [(1, 0, 0), (2, 100, 100)]


@pytest.mark.parametrize("status", [400, 401, 404])
def test_every_listed_terminal_status_ends_the_plan(status):
    responses = [{"status": 503}, {"status": status}, {"status": 200}]
    assert shape(plan(policy(), responses, FOREVER)) == [(1, 0, 0), (2, 100, 100)]


def test_attempts_are_one_indexed_dicts_of_three_int_keys():
    got = plan(policy(max_attempts=3), retryable(3), FOREVER)
    assert [a["number"] for a in got] == [1, 2, 3]
    for a in got:
        assert set(a) == {"number", "start_ms", "delay_ms"}
        assert all(isinstance(v, int) for v in a.values())
    assert got[0]["start_ms"] == 0 and got[0]["delay_ms"] == 0


# --- errors -----------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, deadline",
    [
        ({"base_ms": 0}, FOREVER),
        ({"base_ms": -1}, FOREVER),
        ({"max_attempts": 0}, FOREVER),
        ({"max_attempts": -3}, FOREVER),
        ({}, -1),
    ],
)
def test_policy_is_validated_before_the_record_is_read(kwargs, deadline):
    # An empty record would otherwise short-circuit to an empty plan.
    with pytest.raises(PolicyError):
        plan(policy(**kwargs), [], deadline)
