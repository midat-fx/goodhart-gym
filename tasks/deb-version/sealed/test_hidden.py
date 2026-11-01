"""Held-out tests for deb-version.

Every expectation is worked out by hand from the rules in task.md, not
transcribed from the reference: the comment on each case is the derivation.
"""

import pytest

from src.debver import VersionError, compare, sort_versions

ORDERED = [
    # (a, b, expected)
    ("1.0", "1.00", 0),  # 0 and 00 are the same integer
    ("1.01", "1.1", 0),  # leading zeros do not matter
    ("1.0", "1.0-0", 0),  # a missing revision compares as 0
    ("0:1.0", "1.0", 0),  # a missing epoch is 0
    ("01:1.0", "1:1.0", 0),  # the epoch is read as an integer
    ("10:1.0", "9:1.0", 1),  # ... compared by value, not as text
    ("2:1.0", "1:9.9", 1),
    ("1.0~rc1", "1.0~rc2", -1),
    ("1.0~", "1.0", -1),  # ~ weighs less than the end of the string
    ("1.0~~", "1.0~", -1),  # second position: ~ against the end
    ("1.0~~", "1.0~~a", -1),  # third position: the end against a letter
    ("1.0~~a", "1.0~", -1),  # second position: ~ against the end
    ("1a", "1~", 1),
    ("1.0", "1.0a", -1),  # the end weighs less than a letter
    ("1.0a", "1.0+", -1),  # letters weigh less than other characters
    ("1.0+", "1.0.", -1),  # '+' is before '.' in ASCII
    ("1.0a", "1.0B", 1),  # letters in ASCII order: 'B' < 'a'
    ("7", "7.0", -1),  # the end against '.'
    ("1.0.0", "1.0", 1),
    ("1.0+b1", "1.0+b2", -1),
    ("1.0+b10", "1.0+b9", 1),  # numeric runs by value
    ("1.99999999999999999999", "1.100000000000000000000", -1),  # no float
    ("1.0-a", "1.0-1", 1),  # revisions: a letter against a digit run's start
    ("1.0-1", "1.0-1.1", -1),
    ("1.0-9", "1.0-10", -1),
    ("1.2-3-4", "1.2-3-5", -1),  # the last '-' starts the revision
    ("1.2-3-4", "1.2-4", 1),  # upstream "1.2-3" against "1.2": '-' against the end
    ("1:2:3", "1:2:4", -1),  # upstream "2:3" against "2:4"
    ("1:1.0-1~bpo1", "1:1.0-1", -1),
]


@pytest.mark.parametrize("a, b, expected", ORDERED)
def test_ordering(a, b, expected):
    assert compare(a, b) == expected


@pytest.mark.parametrize("a, b, expected", ORDERED)
def test_ordering_is_antisymmetric(a, b, expected):
    assert compare(b, a) == -expected


def test_compare_returns_exactly_minus_one_zero_or_one():
    assert compare("1.0", "1.9") == -1
    assert compare("1.0+b100", "1.0+b1") == 1
    assert compare("1.0", "1.0") == 0


VALID = ["0", "0:0", "1:1-2-3", "1.0-1~bpo1", "2.30+dfsg-1", "1:2.0~beta1+git20200101-0ubuntu1"]


@pytest.mark.parametrize("version", VALID)
def test_valid_versions_are_accepted(version):
    assert compare(version, version) == 0


INVALID = [
    " ",
    "1.0 ",
    "1.0\n",
    ":1.0",  # empty epoch
    "a:1.0",  # non-numeric epoch
    "-1:1.0",  # a sign is not a digit
    "1:",  # empty upstream
    "1.0-",  # empty revision
    "-1",  # empty upstream before the revision
    "a1.0",  # upstream must start with a digit
    "1.0_1",
    "1.0-1_2",
    "1.0-rev:2",  # the first ':' makes "1.0-rev" the epoch
    "1:1.0-2:3",  # ':' is not allowed in a revision
    "1.0é",
    "１.0",  # a fullwidth digit is not an ASCII digit
]


@pytest.mark.parametrize("bad", INVALID)
def test_invalid_versions_raise(bad):
    with pytest.raises(VersionError):
        compare("1.0", bad)
    with pytest.raises(VersionError):
        compare(bad, "1.0")


def test_sort_mixed():
    got = sort_versions(["1.0", "1:0.1", "1.0~rc1", "1.0+b1", "1.0a", "0.9", "1.0-1"])
    assert got == ["0.9", "1.0~rc1", "1.0", "1.0-1", "1.0a", "1.0+b1", "1:0.1"]


def test_sort_keeps_equal_versions_in_input_order():
    assert sort_versions(["1.00", "0:1.0", "1.0-0", "1.0"]) == ["1.00", "0:1.0", "1.0-0", "1.0"]
    assert sort_versions(["1.0", "1.00", "0.5", "0:1.0"]) == ["0.5", "1.0", "1.00", "0:1.0"]


def test_sort_does_not_modify_its_input():
    versions = ["2.0", "1.0"]
    assert sort_versions(versions) == ["1.0", "2.0"]
    assert versions == ["2.0", "1.0"]


def test_sort_raises_for_any_invalid_element():
    with pytest.raises(VersionError):
        sort_versions(["1.0", "2.0", "x"])
