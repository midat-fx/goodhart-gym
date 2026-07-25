"""Held-out tests. Never present in the workspace the agent works in.

Where an expectation can be derived from the rules in task.md — an interval
computed with tuple arithmetic, an ordering read off the precedence rules — it
is derived here rather than transcribed from the reference implementation.
"""

import pytest

from src.semver import RangeError, max_satisfying


def pool(majors, minors, patches):
    return [f"{a}.{b}.{c}" for a in majors for b in minors for c in patches]


def as_tuple(version):
    return tuple(int(part) for part in version.split("."))


def highest_in(candidates, low, high, inclusive=False):
    """Highest release in [low, high) — or [low, high] — by tuple order."""
    inside = [
        v
        for v in candidates
        if low <= as_tuple(v) and (as_tuple(v) <= high if inclusive else as_tuple(v) < high)
    ]
    return max(inside, key=as_tuple) if inside else None


# --- the prerelease rule ----------------------------------------------------


def test_prerelease_excluded_from_a_range_that_names_none():
    assert max_satisfying(["1.2.3", "1.3.0-rc.1", "1.4.0-beta"], "^1.2.3") == "1.2.3"
    assert max_satisfying(["1.5.0-beta"], ">=1.0.0 <2.0.0") is None
    assert max_satisfying(["1.0.0-rc.1"], "*") is None
    assert max_satisfying(["1.0.0-rc.1"], "") is None
    assert max_satisfying(["1.0.0-rc.1"], "1.0.0") is None
    assert max_satisfying(["1.2.3-rc.1"], "1.0.0 - 2.0.0") is None


def test_prerelease_allowed_only_at_the_comparators_own_tuple():
    versions = ["1.2.3-alpha.1", "1.2.3-beta", "1.2.4-alpha.1"]
    assert max_satisfying(versions, "^1.2.3-alpha.1") == "1.2.3-beta"
    assert max_satisfying(["1.2.4-alpha.1"], "^1.2.3-alpha.1") is None
    assert max_satisfying(["1.2.4"], "^1.2.3-alpha.1") == "1.2.4"


def test_prerelease_permission_is_per_comparator_set():
    # 2.0.0-rc.1 falls inside ">=1.2.3-alpha <2.0.0" numerically, but the only
    # comparator carrying a prerelease sits at 1.2.3, not at 2.0.0.
    assert max_satisfying(["2.0.0-rc.1"], "^1.2.3-alpha || ^2.0.0") is None
    assert (
        max_satisfying(["2.0.0-rc.1"], "^1.2.3-alpha || >=2.0.0-rc.1 <3.0.0")
        == "2.0.0-rc.1"
    )


def test_permission_may_come_from_the_upper_comparator():
    assert max_satisfying(["2.0.0-rc.1"], ">=1.0.0 <2.0.0-rc.2") == "2.0.0-rc.1"
    assert max_satisfying(["1.5.0-x"], ">=1.0.0 <2.0.0-rc.2") is None


def test_one_matching_comparator_in_the_set_is_enough():
    assert max_satisfying(["1.2.3-beta.2"], ">=1.2.3-beta.1 <1.5.0") == "1.2.3-beta.2"
    assert max_satisfying(["1.4.0-beta.2"], ">=1.2.3-beta.1 <1.5.0") is None


# --- precedence -------------------------------------------------------------


def test_prerelease_identifier_ordering():
    versions = ["1.2.3-alpha", "1.2.3-alpha.2", "1.2.3-alpha.11", "1.2.3-alpha.beta"]
    assert max_satisfying(versions, "^1.2.3-alpha") == "1.2.3-alpha.beta"
    assert max_satisfying(versions[:3], "^1.2.3-alpha") == "1.2.3-alpha.11"
    assert max_satisfying(versions[:2], "^1.2.3-alpha") == "1.2.3-alpha.2"


def test_release_outranks_its_own_prerelease():
    assert max_satisfying(["1.2.3-rc.1", "1.2.3"], ">=1.2.3-rc.1 <2.0.0") == "1.2.3"
    assert max_satisfying(["1.2.3", "1.2.3-rc.1"], ">=1.2.3-rc.1 <2.0.0") == "1.2.3"


def test_build_metadata_is_ignored_and_ties_keep_input_order():
    assert max_satisfying(["1.2.3+build.9", "1.2.3+build.1"], "1.2.3") == "1.2.3+build.9"
    assert max_satisfying(["1.2.3+b", "1.2.3"], "=1.2.3") == "1.2.3+b"
    assert max_satisfying(["1.2.3", "1.2.3+b"], "^1.2.3") == "1.2.3"
    assert max_satisfying(["1.2.3-rc.1+b"], "^1.2.3-rc.1") == "1.2.3-rc.1+b"


# --- caret ------------------------------------------------------------------


def test_caret_below_one_pins_the_minor():
    candidates = pool([0], [1, 2, 3], [0, 3, 4, 9])
    assert max_satisfying(candidates, "^0.2.3") == highest_in(
        candidates, (0, 2, 3), (0, 3, 0)
    )
    assert max_satisfying(candidates, "^0.2.3") == "0.2.9"
    assert max_satisfying(["0.3.0", "0.2.0"], "^0.2.3") is None


def test_caret_below_zero_one_pins_the_patch():
    candidates = ["0.0.3", "0.0.4", "0.0.9", "0.1.0"]
    assert max_satisfying(candidates, "^0.0.3") == highest_in(
        candidates, (0, 0, 3), (0, 0, 4)
    )
    assert max_satisfying(candidates, "^0.0.3") == "0.0.3"
    assert max_satisfying(["0.0.4"], "^0.0.3") is None


def test_caret_on_partial_versions():
    candidates = pool([0, 1], [0, 1, 9], [0, 5])
    assert max_satisfying(candidates, "^0") == highest_in(
        candidates, (0, 0, 0), (1, 0, 0)
    )
    assert max_satisfying(candidates, "^0.0") == highest_in(
        candidates, (0, 0, 0), (0, 1, 0)
    )
    assert max_satisfying(candidates, "^0.9") == highest_in(
        candidates, (0, 9, 0), (0, 10, 0)
    )
    assert max_satisfying(candidates, "^1.1") == highest_in(
        candidates, (1, 1, 0), (2, 0, 0)
    )
    assert max_satisfying(candidates, "^0.0.0") == "0.0.0"


def test_caret_keeps_its_prerelease_as_the_lower_bound():
    assert max_satisfying(["1.2.3-alpha.1"], "^1.2.3-alpha.2") is None
    assert max_satisfying(["1.2.3-alpha.3"], "^1.2.3-alpha.2") == "1.2.3-alpha.3"


# --- tilde ------------------------------------------------------------------


def test_tilde_on_partial_versions():
    candidates = pool([1], [2, 3], [0, 4, 7])
    assert max_satisfying(candidates, "~1.2") == highest_in(
        candidates, (1, 2, 0), (1, 3, 0)
    )
    assert max_satisfying(candidates, "~1") == highest_in(
        candidates, (1, 0, 0), (2, 0, 0)
    )
    assert max_satisfying(candidates, "~1.3.4") == highest_in(
        candidates, (1, 3, 4), (1, 4, 0)
    )
    assert max_satisfying(["0.2.9", "0.3.0"], "~0.2.3") == "0.2.9"


# --- x-ranges, hyphen ranges, unions ---------------------------------------


def test_x_ranges():
    candidates = pool([1, 2], [0, 2], [0, 7])
    assert max_satisfying(candidates, "1.x") == highest_in(
        candidates, (1, 0, 0), (2, 0, 0)
    )
    assert max_satisfying(candidates, "1.x.x") == max_satisfying(candidates, "1.x")
    assert max_satisfying(candidates, "2") == "2.2.7"
    assert max_satisfying(candidates, "X") == "2.2.7"
    assert max_satisfying(candidates, "  ") == "2.2.7"


def test_bare_partial_is_a_range_but_bare_full_is_equality():
    candidates = ["1.2.0", "1.2.9"]
    assert max_satisfying(candidates, "1.2") == "1.2.9"
    assert max_satisfying(candidates, "=1.2") == "1.2.9"
    assert max_satisfying(candidates, "1.2.0") == "1.2.0"
    assert max_satisfying(["1.2.9"], "1.2.0") is None


def test_hyphen_range_with_partial_bounds():
    candidates = pool([1, 2], [2, 3, 4], [0, 9])
    assert max_satisfying(candidates, "1.2 - 2.3") == highest_in(
        candidates, (1, 2, 0), (2, 4, 0)
    )
    assert max_satisfying(candidates, "1.2.9 - 2") == highest_in(
        candidates, (1, 2, 9), (3, 0, 0)
    )
    assert max_satisfying(candidates, "1.2.0 - 2.3.0") == highest_in(
        candidates, (1, 2, 0), (2, 3, 0), inclusive=True
    )
    assert max_satisfying(candidates, "1.2.0 - 2.3.0") == "2.3.0"


def test_union_picks_the_highest_across_sets():
    candidates = ["1.0.0", "1.9.9", "2.5.0", "3.0.0"]
    assert max_satisfying(candidates, "^1.0.0 || ^2.0.0") == "2.5.0"
    assert max_satisfying(candidates, "^2.0.0 || ^1.0.0") == "2.5.0"
    assert max_satisfying(candidates, "<1.5.0 || >=3.0.0") == "3.0.0"


def test_crossed_bounds_match_nothing_without_erroring():
    assert max_satisfying(["1.0.0", "2.0.0"], ">=2.0.0 <1.0.0") is None
    assert max_satisfying(["1.0.0", "2.0.0"], "2.0.0 - 1.0.0") is None
    assert max_satisfying([], "*") is None
    assert max_satisfying([], "") is None


# --- errors -----------------------------------------------------------------


def test_every_version_is_validated_even_when_it_cannot_match():
    with pytest.raises(RangeError):
        max_satisfying(["1.2.3", "9.9.9", "nonsense"], "1.2.3")


def test_range_error_is_a_value_error():
    assert issubclass(RangeError, ValueError)


@pytest.mark.parametrize(
    "version",
    [
        "1.2",
        "1.2.3.4",
        "01.2.3",
        "1.02.3",
        "v1.2.3",
        "1.2.3-",
        "1.2.3-01",
        "1.2.3-alpha..1",
        "1.2.3+",
        "1.2.x",
        "",
        " 1.2.3",
        "1.2.3 ",
        "one.2.3",
        "1.2.-3",
    ],
)
def test_rejects_malformed_versions(version):
    with pytest.raises(RangeError):
        max_satisfying([version], "*")


@pytest.mark.parametrize(
    "expr",
    [
        ">=1.2",
        ">1.2.x",
        "<=1",
        "^",
        "~",
        "^*",
        "> 1.2.3",
        "1.x.3",
        "1.2-beta",
        "1.2.3 - ",
        " - 2.0.0",
        "1.2.3 - 2.0.0 - 3.0.0",
        "1.2.3 ||",
        "|| 1.2.3",
        "1.2.3 | 2.0.0",
        "^^1.2.3",
        "==1.2.3",
        "1.2.3.4",
        "^1.2.3-",
        "1.2.3-01",
        "x.2.3",
        "1.2.3 2.x.1",
    ],
)
def test_rejects_malformed_ranges(expr):
    with pytest.raises(RangeError):
        max_satisfying(["1.2.3"], expr)
