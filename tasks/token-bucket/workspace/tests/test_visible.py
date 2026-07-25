import pytest

from src.bucket import ConfigError, Decision, Event, decide

# A five-token bucket refilled at three tokens per second.
CONFIG = {"capacity": 5, "refill_tokens": 3, "refill_interval_ms": 1000}


def empty(**overrides):
    return {**CONFIG, "initial_tokens": 0, **overrides}


def test_full_bucket_drains_one_token_at_a_time():
    got = decide(CONFIG, [Event(0, "a", 1)] * 5)
    assert got[0] == Decision(True, 4, 0)
    assert got == [(True, 4, 0), (True, 3, 0), (True, 2, 0), (True, 1, 0), (True, 0, 0)]


def test_denied_once_the_bucket_is_empty():
    got = decide(CONFIG, [Event(0, "a", 1)] * 5 + [Event(0, "a", 3)])
    assert got[-1] == (False, 0, 1000)


def test_a_denied_request_takes_no_tokens():
    got = decide(empty(), [Event(0, "a", 3), Event(1000, "a", 1)])
    assert got == [(False, 0, 1000), (True, 2, 0)]


def test_retry_after_shrinks_as_tokens_accrue():
    got = decide(empty(), [Event(0, "a", 3), Event(700, "a", 3)])
    assert got == [(False, 0, 1000), (False, 2, 300)]


def test_fractional_tokens_carry_forward():
    events = [Event(0, "a", 1)] * 5 + [Event(500, "a", 1), Event(1500, "a", 1)]
    # 1.5 tokens have accrued by 500ms; 0.5 is carried past the second grant.
    assert decide(CONFIG, events)[5:] == [(True, 0, 0), (True, 2, 0)]


def test_keys_get_independent_buckets():
    events = [Event(0, "a", 5), Event(0, "b", 2), Event(0, "a", 3)]
    assert decide(CONFIG, events) == [(True, 0, 0), (True, 3, 0), (False, 0, 1000)]


def test_initial_tokens_replaces_a_full_bucket():
    assert decide({**CONFIG, "initial_tokens": 2}, [Event(0, "a", 1)]) == [(True, 1, 0)]
    assert decide(CONFIG, [Event(0, "a", 1)]) == [(True, 4, 0)]


def test_no_events():
    assert decide(CONFIG, []) == []


@pytest.mark.parametrize(
    "config, events",
    [
        ({**CONFIG, "capacity": 0}, [Event(0, "a", 1)]),
        (CONFIG, [Event(0, "a", -1)]),
        (CONFIG, [Event(10, "a", 1), Event(5, "a", 1)]),
    ],
)
def test_rejects_bad_input(config, events):
    with pytest.raises(ConfigError):
        decide(config, events)
