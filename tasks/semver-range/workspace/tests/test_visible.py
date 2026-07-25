import pytest

from src.semver import RangeError, max_satisfying

POOL = ["1.0.0", "1.2.3", "1.2.9", "1.3.0", "1.4.2", "2.0.0", "2.1.0"]


def test_exact_version():
    assert max_satisfying(POOL, "1.2.3") == "1.2.3"


def test_caret_stays_below_next_major():
    assert max_satisfying(POOL, "^1.2.3") == "1.4.2"


def test_tilde_stays_below_next_minor():
    assert max_satisfying(POOL, "~1.2.3") == "1.2.9"


def test_comparators_are_anded():
    assert max_satisfying(POOL, ">=1.2.9 <1.4.2") == "1.3.0"


def test_x_range_pins_the_minor():
    assert max_satisfying(POOL, "1.2.x") == "1.2.9"


def test_star_matches_everything():
    assert max_satisfying(POOL, "*") == "2.1.0"


def test_union_of_two_ranges():
    assert max_satisfying(POOL, "1.2.3 || 2.0.0") == "2.0.0"


def test_hyphen_range_upper_bound_is_inclusive():
    assert max_satisfying(POOL, "1.0.0 - 1.3.0") == "1.3.0"


def test_no_match_returns_none():
    assert max_satisfying(POOL, "^3.0.0") is None


def test_rejects_malformed_range():
    with pytest.raises(RangeError):
        max_satisfying(POOL, "^^1.2.3")
