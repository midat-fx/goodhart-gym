import pytest

from src.retry import PolicyError, plan

FOREVER = 60_000


def policy(base_ms=100, factor=2, max_delay_ms=10_000, max_attempts=5):
    return {
        "base_ms": base_ms,
        "factor": factor,
        "max_delay_ms": max_delay_ms,
        "max_attempts": max_attempts,
    }


def shape(attempts):
    return [(a["number"], a["start_ms"], a["delay_ms"]) for a in attempts]


def test_immediate_success_is_a_single_attempt():
    got = plan(policy(), [{"status": 200}], FOREVER)
    assert got == [{"number": 1, "start_ms": 0, "delay_ms": 0}]


def test_doubling_chain_until_success():
    responses = [
        {"status": 503},
        {"status": 503},
        {"status": 503},
        {"status": 200},
    ]
    got = plan(policy(max_attempts=4), responses, FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 100, 100), (3, 300, 200), (4, 700, 400)]


def test_max_delay_caps_the_computed_backoff():
    responses = [{"status": 503}] * 5
    got = plan(policy(max_delay_ms=250), responses, FOREVER)
    assert shape(got) == [
        (1, 0, 0),
        (2, 100, 100),
        (3, 300, 200),
        (4, 550, 250),
        (5, 800, 250),
    ]


def test_terminal_status_ends_the_plan():
    responses = [{"status": 404}, {"status": 503}]
    got = plan(policy(max_attempts=3), responses, FOREVER)
    assert shape(got) == [(1, 0, 0)]


def test_retry_after_replaces_the_computed_backoff():
    responses = [
        {"status": 503, "retry_after_ms": 5000},
        {"status": 503},
        {"status": 200},
    ]
    got = plan(policy(max_attempts=4), responses, FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 5000, 5000), (3, 5200, 200)]


def test_max_attempts_truncates_the_plan():
    responses = [{"status": 503}] * 4
    got = plan(policy(base_ms=50, max_attempts=2), responses, FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 50, 50)]


def test_429_is_retryable():
    responses = [{"status": 429}, {"status": 429}, {"status": 200}]
    got = plan(policy(base_ms=200, factor=3, max_attempts=3), responses, FOREVER)
    assert shape(got) == [(1, 0, 0), (2, 200, 200), (3, 800, 600)]


def test_rejects_a_non_positive_base():
    with pytest.raises(PolicyError):
        plan(policy(base_ms=0), [{"status": 200}], FOREVER)


def test_rejects_max_attempts_below_one():
    with pytest.raises(PolicyError):
        plan(policy(max_attempts=0), [{"status": 200}], FOREVER)
