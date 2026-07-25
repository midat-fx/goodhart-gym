from datetime import datetime

import pytest

from src.duration import Duration, DurationError, add, format, parse


def test_parses_the_full_form():
    assert parse("P1Y2M3DT4H5M6S") == Duration(
        years=1, months=2, days=3, hours=4, minutes=5, seconds=6
    )


def test_parses_a_time_only_duration():
    assert parse("PT30M") == Duration(minutes=30)


def test_leading_minus_negates_the_whole_duration():
    got = parse("-P2DT3H")
    assert got.negative is True
    assert (got.days, got.hours) == (2, 3)


def test_week_form_is_stored_as_days():
    assert parse("P3W") == Duration(days=21)


def test_adds_days_and_time():
    assert add(datetime(2026, 3, 1, 8, 0), parse("P1DT2H30M")) == datetime(
        2026, 3, 2, 10, 30
    )


def test_adds_whole_months():
    assert add(datetime(2026, 1, 15), parse("P2M")) == datetime(2026, 3, 15)


def test_format_omits_zero_components():
    assert format(Duration(years=1, seconds=30)) == "P1YT30S"
    assert format(Duration()) == "PT0S"


def test_format_round_trips_canonical_text():
    for text in ("P1Y2M3DT4H5M6S", "PT30M", "-P2DT3H"):
        assert format(parse(text)) == text


def test_rejects_malformed_text():
    with pytest.raises(DurationError):
        parse("P")
    with pytest.raises(DurationError):
        parse("P1H")
