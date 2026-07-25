"""Held-out tests. Never present in the workspace the agent works in.

Where possible an expectation is derived independently (from `datetime`)
rather than transcribed from the reference implementation.
"""

from datetime import date, datetime

import pytest

from src.cron import CronError, next_firings


def test_dom_and_dow_are_ored_when_both_restricted():
    got = next_firings("0 0 1 * MON", datetime(2026, 2, 28, 23, 59), 8)
    march = [m.day for m in got if (m.year, m.month) == (2026, 3)]
    expected = sorted(
        {1} | {d for d in range(1, 32) if date(2026, 3, d).weekday() == 0}
    )
    assert march == expected


def test_only_dow_restricted_selects_that_weekday():
    got = next_firings("0 0 * * SUN", datetime(2026, 3, 1, 0, 0), 4)
    assert all(m.weekday() == 6 for m in got)
    assert [m.day for m in got] == [8, 15, 22, 29]


def test_seven_is_sunday():
    by_name = next_firings("0 0 * * SUN", datetime(2026, 3, 1, 0, 0), 3)
    by_seven = next_firings("0 0 * * 7", datetime(2026, 3, 1, 0, 0), 3)
    by_zero = next_firings("0 0 * * 0", datetime(2026, 3, 1, 0, 0), 3)
    assert by_name == by_seven == by_zero


def test_star_slash_one_counts_as_restricted():
    # dow "*/1" matches every weekday but is restricted, so the OR rule makes
    # every day match. Plain "*" leaves only the day-of-month rule.
    ored = next_firings("0 0 1 * */1", datetime(2026, 3, 2, 0, 0), 3)
    assert [m.day for m in ored] == [3, 4, 5]

    dom_only = next_firings("0 0 1 * *", datetime(2026, 3, 2, 0, 0), 2)
    assert [(m.month, m.day) for m in dom_only] == [(4, 1), (5, 1)]


def test_step_inside_a_range():
    got = next_firings("0 8-18/4 * * *", datetime(2026, 3, 1, 0, 0), 4)
    assert [m.hour for m in got] == [8, 12, 16, 8]


def test_bare_value_with_step_runs_to_field_maximum():
    got = next_firings("0 5/6 * * *", datetime(2026, 3, 1, 0, 0), 5)
    assert [m.hour for m in got] == [5, 11, 17, 23, 5]


def test_month_names_in_a_range():
    got = next_firings("0 0 15 FEB-APR *", datetime(2026, 1, 1, 0, 0), 4)
    assert [(m.month, m.day) for m in got] == [(2, 15), (3, 15), (4, 15), (2, 15)]


def test_names_are_case_insensitive():
    lower = next_firings("0 0 * * fri", datetime(2026, 3, 1, 0, 0), 2)
    upper = next_firings("0 0 * * FRI", datetime(2026, 3, 1, 0, 0), 2)
    assert lower == upper
    assert all(m.weekday() == 4 for m in lower)


def test_leap_day_skips_to_the_next_leap_year():
    got = next_firings("0 0 29 2 *", datetime(2026, 3, 1, 0, 0), 1)
    assert got == [datetime(2028, 2, 29, 0, 0)]


def test_year_rollover():
    got = next_firings("30 23 31 12 *", datetime(2026, 12, 31, 23, 45), 2)
    assert got == [datetime(2027, 12, 31, 23, 30), datetime(2028, 12, 31, 23, 30)]


def test_start_seconds_are_truncated_not_rounded_up():
    got = next_firings("* * * * *", datetime(2026, 3, 1, 10, 0, 30), 1)
    assert got == [datetime(2026, 3, 1, 10, 1)]


def test_never_fires_within_five_years():
    with pytest.raises(CronError):
        next_firings("0 0 30 2 *", datetime(2026, 3, 1, 0, 0), 1)


@pytest.mark.parametrize(
    "expr",
    [
        "0 0 * * 8",
        "60 0 * * *",
        "0 24 * * *",
        "0 0 0 * *",
        "0 0 * 13 *",
        "*/0 * * * *",
        "10-5 * * * *",
        "x * * * *",
        "0 0 * * MOO",
        "0,, 0 * * *",
        "* * * * * *",
        "",
    ],
)
def test_rejects_malformed_expressions(expr):
    with pytest.raises(CronError):
        next_firings(expr, datetime(2026, 3, 1, 0, 0), 1)
