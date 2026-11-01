import pytest

from src.debver import VersionError, compare, sort_versions


def test_numeric_runs_compare_by_value():
    assert compare("1.2", "1.10") == -1
    assert compare("1.10", "1.2") == 1


def test_identical_versions_are_equal():
    assert compare("2.4.1", "2.4.1") == 0


def test_the_epoch_decides_first():
    assert compare("1:0.1", "9.9") == 1


def test_tilde_sorts_before_the_release():
    assert compare("1.0~rc1", "1.0") == -1


def test_the_revision_breaks_ties():
    assert compare("3.1-1", "3.1-2") == -1


def test_sort_versions_orders_ascending():
    assert sort_versions(["2.0", "1.0", "1.5"]) == ["1.0", "1.5", "2.0"]


def test_sort_an_empty_list():
    assert sort_versions([]) == []


@pytest.mark.parametrize("bad", ["", "abc", "1.0 beta"])
def test_rejects_invalid_versions(bad):
    with pytest.raises(VersionError):
        compare(bad, "1.0")
