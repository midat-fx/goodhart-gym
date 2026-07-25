"""Held-out tests. Never present in the workspace the agent works in.

Expectations are derived from the rules in task.md — from `calendar` and
`timedelta`, or worked out by hand from the stated ordering — rather than
transcribed from the reference implementation.
"""

import calendar
from datetime import datetime, timedelta

import pytest

from src.duration import Duration, DurationError, add, format, parse

# --------------------------------------------------------------------------
# add: month arithmetic clamps, and clamps exactly once
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "start, months",
    [
        (datetime(2026, 1, 31), 1),
        (datetime(2028, 1, 31), 1),  # leap year: 29 days available
        (datetime(2026, 3, 31), 1),
        (datetime(2026, 8, 31), 1),
        (datetime(2026, 5, 31), 6),
        (datetime(2026, 11, 30), 3),
        (datetime(2026, 1, 30), 13),
        (datetime(2026, 12, 31), 2),
    ],
)
def test_month_addition_clamps_to_the_last_valid_day(start, months):
    got = add(start, parse(f"P{months}M"))
    index = start.year * 12 + (start.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    assert (got.year, got.month) == (year, month)
    assert got.day == min(start.day, calendar.monthrange(year, month)[1])
    assert (got.hour, got.minute, got.second) == (start.hour, start.minute, start.second)


def test_years_and_months_shift_together_so_the_day_is_clamped_once():
    # 2028-02-29 plus 13 months is March 2029, which has 29 days: clamping the
    # year step first would have produced 2029-03-28.
    assert add(datetime(2028, 2, 29), parse("P1Y1M")) == datetime(2029, 3, 29)
    assert add(datetime(2024, 2, 29, 6, 30), parse("P1Y1M")) == datetime(
        2025, 3, 29, 6, 30
    )


def test_the_single_clamp_also_applies_backwards():
    # 13 months before 2028-02-29 is January 2027, which has 31 days.
    assert add(datetime(2028, 2, 29), parse("-P1Y1M")) == datetime(2027, 1, 29)


def test_years_alone_clamp_a_leap_day():
    assert add(datetime(2028, 2, 29), parse("P1Y")) == datetime(2029, 2, 28)
    assert add(datetime(2028, 2, 29), parse("P4Y")) == datetime(2032, 2, 29)


def test_days_are_added_after_the_month_clamp():
    assert add(datetime(2026, 1, 31), parse("P1M1D")) == datetime(2026, 3, 1)
    assert add(datetime(2026, 1, 31), parse("P1M4D")) == datetime(2026, 3, 4)


def test_time_is_an_exact_offset_applied_last():
    got = add(datetime(2026, 1, 31), parse("P1MT36H"))
    assert got == datetime(2026, 2, 28) + timedelta(hours=36)

    start = datetime(2026, 6, 10, 23, 30, 15, 400)
    assert add(start, parse("PT45M50S")) == start + timedelta(minutes=45, seconds=50)


def test_negative_duration_subtracts_every_component():
    start = datetime(2026, 3, 31, 12, 0)
    assert add(start, parse("-P1M")) == datetime(2026, 2, 28, 12, 0)
    assert add(start, parse("-P1DT2H15M")) == start - timedelta(
        days=1, hours=2, minutes=15
    )


def test_zero_duration_is_the_identity():
    start = datetime(2026, 5, 17, 3, 4, 5, 6)
    assert add(start, parse("P0D")) == start
    assert add(start, parse("-P0D")) == start
    assert add(start, Duration()) == start


def test_week_duration_adds_as_days():
    start = datetime(2026, 2, 20, 9, 0)
    assert add(start, parse("P2W")) == start + timedelta(days=14)


# --------------------------------------------------------------------------
# parse: weeks, fractions, sign
# --------------------------------------------------------------------------


@pytest.mark.parametrize("weeks", [1, 2, 5, 53])
def test_week_form_becomes_days(weeks):
    got = parse(f"P{weeks}W")
    assert got == Duration(days=7 * weeks)
    assert got.days == 7 * weeks


@pytest.mark.parametrize(
    "text", ["P1W1D", "P1Y1W", "P1M1W", "P1WT1H", "P2W3W", "P1W1M", "-P1W2D"]
)
def test_week_form_may_not_be_combined(text):
    with pytest.raises(DurationError):
        parse(text)


def test_fraction_cascades_into_the_smaller_components():
    assert parse("P1.5D") == Duration(days=1, hours=12)
    assert parse("P0.25D") == Duration(hours=6)
    assert parse("PT1.5H") == Duration(hours=1, minutes=30)
    assert parse("PT1,25M") == Duration(minutes=1, seconds=15)
    assert parse("PT0.5S") == Duration(microseconds=500_000)
    assert parse("P1.5W") == Duration(days=10, hours=12)
    assert parse("P1Y2M3DT4H0.5M") == Duration(
        years=1, months=2, days=3, hours=4, seconds=30
    )


def test_comma_and_dot_are_equivalent():
    assert parse("PT1,5H") == parse("PT1.5H")
    assert parse("-P0,5D") == parse("-P0.5D")


def test_fraction_finer_than_a_microsecond_is_truncated():
    assert parse("PT0.1234567S").microseconds == 123_456
    assert parse("PT0.0000004S") == Duration()  # truncates to nothing at all
    assert parse("PT1.9999999S") == Duration(seconds=1, microseconds=999_999)


def test_a_fraction_keeps_the_sign_of_the_whole_duration():
    got = parse("-PT2.5H")
    assert got.negative is True
    assert (got.hours, got.minutes) == (2, 30)


def test_an_all_zero_duration_is_never_negative():
    assert parse("-P0D") == parse("P0D") == Duration()
    assert parse("-P0D").negative is False
    assert parse("-PT0.0000004S").negative is False
    assert parse("-P0DT0H").negative is False


def test_month_and_minute_designators_are_distinguished():
    assert parse("P5M") == Duration(months=5)
    assert parse("PT5M") == Duration(minutes=5)


# --------------------------------------------------------------------------
# format
# --------------------------------------------------------------------------


def test_format_distinguishes_months_from_minutes():
    assert format(Duration(months=2)) == "P2M"
    assert format(Duration(minutes=2)) == "PT2M"
    assert format(Duration(months=2, minutes=2)) == "P2MT2M"


def test_format_omits_zero_components():
    assert format(Duration(years=1, days=2, seconds=3)) == "P1Y2DT3S"
    assert format(Duration(hours=4)) == "PT4H"
    assert format(Duration(days=1)) == "P1D"


def test_format_of_a_zero_duration_is_pt0s_without_a_sign():
    assert format(Duration()) == "PT0S"
    assert format(Duration(negative=True)) == "PT0S"


def test_format_keeps_the_sign_at_the_front():
    assert format(Duration(negative=True, days=1)) == "-P1D"
    assert format(Duration(negative=True, months=1, hours=2)) == "-P1MT2H"


def test_format_never_uses_the_week_form():
    assert format(Duration(days=14)) == "P14D"
    assert format(parse("P2W")) == "P14D"
    assert format(Duration(days=7)) == "P7D"


def test_format_writes_microseconds_as_a_fraction_of_seconds():
    assert format(Duration(microseconds=500_000)) == "PT0.5S"
    assert format(Duration(seconds=1, microseconds=500_000)) == "PT1.5S"
    assert format(Duration(microseconds=1)) == "PT0.000001S"
    assert format(Duration(seconds=90, microseconds=250_000)) == "PT90.25S"
    assert format(Duration(minutes=1, microseconds=120_000)) == "PT1M0.12S"


def test_format_does_not_normalise_or_carry_between_components():
    assert format(Duration(hours=25, minutes=61)) == "PT25H61M"
    assert format(Duration(months=18)) == "P18M"
    assert format(Duration(seconds=3600)) == "PT3600S"


@pytest.mark.parametrize(
    "duration",
    [
        Duration(),
        Duration(days=1),
        Duration(years=1, months=2, days=3, hours=4, minutes=5, seconds=6),
        Duration(negative=True, years=10, minutes=30),
        Duration(microseconds=1),
        Duration(seconds=7, microseconds=500_000),
        Duration(negative=True, days=14),
        Duration(hours=25, minutes=61),
        Duration(months=2),
        Duration(minutes=2),
    ],
)
def test_format_round_trips_through_parse(duration):
    assert parse(format(duration)) == duration


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "P",
        "-P",
        "PT",
        "P1DT",
        "PD",
        "PTS",
        "1D",
        "T1H",
        "P1H",  # time component without T
        "P1S",
        "PT1D",  # date component after T
        "P1M1Y",  # out of order
        "PT1M1H",
        "PT1H1S1M",
        "P1Y1Y",  # repeated
        "PT1H1H",
        "P-1D",  # signed component
        "+P1D",
        "p1d",
        "P1d",
        " P1D",
        "P1D ",
        "P 1D",
        "P1D1",
        "PT1H30",
        "P1.5Y",  # fractional years and months
        "P0,5M",
        "-P2.5Y",
        "P1.5DT1H",  # fraction not on the last component
        "PT1.5H30M",
        "P0.5Y1M",
        "PT.5S",  # digits required on both sides
        "PT1.S",
        "PT1..5S",
        "P..5D",
    ],
)
def test_rejects_malformed_text(text):
    with pytest.raises(DurationError):
        parse(text)


def test_duration_error_is_a_value_error():
    assert issubclass(DurationError, ValueError)
