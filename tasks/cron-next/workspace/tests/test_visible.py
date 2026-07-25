from datetime import datetime

import pytest

from src.cron import CronError, next_firings


def dt(*args):
    return datetime(*args)


def test_every_minute():
    got = next_firings("* * * * *", dt(2026, 3, 1, 10, 0), 3)
    assert got == [dt(2026, 3, 1, 10, 1), dt(2026, 3, 1, 10, 2), dt(2026, 3, 1, 10, 3)]


def test_daily_at_fixed_time():
    got = next_firings("30 4 * * *", dt(2026, 3, 1, 10, 0), 2)
    assert got == [dt(2026, 3, 2, 4, 30), dt(2026, 3, 3, 4, 30)]


def test_start_is_exclusive():
    got = next_firings("0 12 * * *", dt(2026, 3, 1, 12, 0), 1)
    assert got == [dt(2026, 3, 2, 12, 0)]


def test_list_of_minutes():
    got = next_firings("0,15,45 9 * * *", dt(2026, 3, 1, 9, 15), 2)
    assert got == [dt(2026, 3, 1, 9, 45), dt(2026, 3, 2, 9, 0)]


def test_step_over_whole_range():
    got = next_firings("*/20 0 * * *", dt(2026, 3, 1, 0, 0), 3)
    assert got == [dt(2026, 3, 1, 0, 20), dt(2026, 3, 1, 0, 40), dt(2026, 3, 2, 0, 0)]


def test_day_of_month_only():
    got = next_firings("0 0 1 * *", dt(2026, 3, 15, 0, 0), 2)
    assert got == [dt(2026, 4, 1, 0, 0), dt(2026, 5, 1, 0, 0)]


def test_count_zero():
    assert next_firings("* * * * *", dt(2026, 3, 1, 10, 0), 0) == []


def test_rejects_wrong_field_count():
    with pytest.raises(CronError):
        next_firings("* * * *", dt(2026, 3, 1, 10, 0), 1)
