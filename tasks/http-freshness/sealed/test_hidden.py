"""Held-out tests. Never present in the workspace the agent works in.

Every input here is absent from `tests/fixtures/cases.json`, and every header
date is derived from an epoch with `datetime` rather than transcribed. The
expected ages and lifetimes are worked out from the arithmetic in task.md, shown
in a comment wherever it is not obvious.
"""

from datetime import datetime, timezone

import pytest

from src.freshness import HeaderError, Result, evaluate

BASE = 1780315200  # Mon, 01 Jun 2026 12:00:00 GMT

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = (
    None, "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def http_date(epoch: int) -> str:
    """Render an epoch as an IMF-fixdate without touching the locale."""
    t = datetime.fromtimestamp(epoch, timezone.utc)
    return (
        f"{_DAYS[t.weekday()]}, {t.day:02d} {_MONTHS[t.month]} {t.year:04d} "
        f"{t.hour:02d}:{t.minute:02d}:{t.second:02d} GMT"
    )


def ev(response, request=None, request_time=BASE, response_time=BASE, now=BASE):
    return evaluate(response, request or {}, request_time, response_time, now)


def test_http_date_helper_round_trips():
    assert http_date(BASE) == "Mon, 01 Jun 2026 12:00:00 GMT"
    assert http_date(0) == "Thu, 01 Jan 1970 00:00:00 GMT"


# --------------------------------------------------------------------------
# current_age: the request-latency term
# --------------------------------------------------------------------------


def test_response_delay_is_part_of_corrected_age():
    # delay 40, Age 5 -> corrected 45; apparent 0; resident 10 -> age 55.
    # Dropping the delay term would give 15, and would call this FRESH.
    got = ev(
        {"Date": http_date(BASE + 40), "Age": "5", "Cache-Control": "max-age=50"},
        request_time=BASE,
        response_time=BASE + 40,
        now=BASE + 50,
    )
    assert got.current_age == 55
    assert got.freshness_lifetime == 50
    assert got.verdict == "STALE"


def test_response_delay_counts_even_without_an_age_header():
    # delay 120, no Age -> corrected 120; apparent 0; resident 0 -> age 120.
    got = ev(
        {"Date": http_date(BASE + 120), "Cache-Control": "max-age=300"},
        request_time=BASE,
        response_time=BASE + 120,
        now=BASE + 120,
    )
    assert got.current_age == 120
    assert got.verdict == "FRESH"


def test_apparent_age_wins_when_it_exceeds_corrected_age():
    # apparent = 100, corrected = 0 + 90 = 90, resident = 30 -> age 130.
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=200"},
        request_time=BASE + 10,
        response_time=BASE + 100,
        now=BASE + 130,
    )
    assert got.current_age == 130
    assert got.verdict == "FRESH"


def test_date_in_the_future_does_not_make_age_negative():
    got = ev(
        {"Date": http_date(BASE + 3600), "Cache-Control": "max-age=60"},
        now=BASE,
    )
    assert got.current_age == 0
    assert got.verdict == "FRESH"


def test_missing_date_falls_back_to_response_time():
    # No Date -> apparent age 0; Expires - response_time = 300.
    got = ev(
        {"Expires": http_date(BASE + 300)},
        now=BASE + 100,
    )
    assert got.current_age == 100
    assert got.freshness_lifetime == 300
    assert got.verdict == "FRESH"


def test_malformed_age_header_is_ignored_not_fatal():
    got = ev(
        {"Date": http_date(BASE), "Age": "about ten", "Cache-Control": "max-age=600"},
        now=BASE + 100,
    )
    assert got.current_age == 100
    assert got.verdict == "FRESH"


# --------------------------------------------------------------------------
# heuristic freshness
# --------------------------------------------------------------------------


def test_heuristic_is_a_tenth_of_the_document_age():
    headers = {
        "Date": http_date(BASE),
        "Last-Modified": http_date(BASE - 10000),
    }
    assert ev(headers, now=BASE + 999).freshness_lifetime == 1000
    assert ev(headers, now=BASE + 999).verdict == "FRESH"
    assert ev(headers, now=BASE + 1000).verdict == "STALE"


def test_heuristic_rounds_down():
    got = ev({"Date": http_date(BASE), "Last-Modified": http_date(BASE - 95)})
    assert got.freshness_lifetime == 9


def test_expires_beats_last_modified():
    got = ev(
        {
            "Date": http_date(BASE),
            "Expires": http_date(BASE + 300),
            "Last-Modified": http_date(BASE - 10000),
        },
        now=BASE + 500,
    )
    assert got.freshness_lifetime == 300
    assert got.verdict == "STALE"


def test_max_age_beats_last_modified():
    got = ev(
        {
            "Date": http_date(BASE),
            "Cache-Control": "max-age=30",
            "Last-Modified": http_date(BASE - 10000),
        },
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 30
    assert got.verdict == "STALE"


def test_no_lifetime_information_at_all_means_zero():
    got = ev({"Date": http_date(BASE)}, now=BASE)
    assert got.current_age == 0
    assert got.freshness_lifetime == 0
    assert got.verdict == "STALE"  # 0 > 0 is false


def test_expires_before_date_clamps_to_zero():
    got = ev(
        {"Date": http_date(BASE), "Expires": http_date(BASE - 3600)},
        now=BASE + 10,
    )
    assert got.freshness_lifetime == 0
    assert got.verdict == "STALE"


# --------------------------------------------------------------------------
# must-revalidate and max-stale
# --------------------------------------------------------------------------


def test_must_revalidate_beats_max_stale():
    stale = {"Date": http_date(BASE), "Cache-Control": "max-age=60, must-revalidate"}
    got = ev(stale, {"Cache-Control": "max-stale=3600"}, now=BASE + 1000)
    assert got.verdict == "MUST_REVALIDATE"
    assert got.current_age == 1000
    assert got.freshness_lifetime == 60


def test_without_must_revalidate_the_same_max_stale_rescues_it():
    ok = {"Date": http_date(BASE), "Cache-Control": "max-age=60"}
    got = ev(ok, {"Cache-Control": "max-stale=3600"}, now=BASE + 1000)
    assert got.verdict == "FRESH"


def test_must_revalidate_beats_bare_max_stale():
    stale = {"Date": http_date(BASE), "Cache-Control": "max-age=60, must-revalidate"}
    got = ev(stale, {"Cache-Control": "max-stale"}, now=BASE + 1000)
    assert got.verdict == "MUST_REVALIDATE"


def test_no_store_beats_max_stale():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "no-store, max-age=60"},
        {"Cache-Control": "max-stale"},
        now=BASE + 1000,
    )
    assert got.verdict == "MUST_REVALIDATE"


def test_bare_max_stale_tolerates_any_staleness():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=60"},
        {"Cache-Control": "max-stale"},
        now=BASE + 10 ** 6,
    )
    assert got.verdict == "FRESH"


def test_max_stale_boundary_is_inclusive():
    stale = {"Date": http_date(BASE), "Cache-Control": "max-age=60"}
    # age 1000, lifetime 60 -> staleness 940.
    assert ev(stale, {"Cache-Control": "max-stale=940"}, now=BASE + 1000).verdict == "FRESH"
    assert ev(stale, {"Cache-Control": "max-stale=939"}, now=BASE + 1000).verdict == "STALE"


def test_unparseable_max_stale_is_ignored():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=60"},
        {"Cache-Control": "max-stale=soon"},
        now=BASE + 1000,
    )
    assert got.verdict == "STALE"


# --------------------------------------------------------------------------
# min-fresh and request max-age
# --------------------------------------------------------------------------


def test_min_fresh_requires_headroom():
    headers = {"Date": http_date(BASE), "Cache-Control": "max-age=600"}
    # age 100: fresh while 600 > 100 + min_fresh.
    assert ev(headers, {"Cache-Control": "min-fresh=499"}, now=BASE + 100).verdict == "FRESH"
    assert ev(headers, {"Cache-Control": "min-fresh=500"}, now=BASE + 100).verdict == "STALE"


def test_min_fresh_does_not_change_the_reported_lifetime():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=600"},
        {"Cache-Control": "min-fresh=5000"},
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 600
    assert got.current_age == 100
    assert got.verdict == "STALE"


def test_max_stale_overrides_an_unsatisfied_min_fresh():
    # Step 2 fails (600 > 100 + 900 is false); step 3 sees staleness -500 <= 0.
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=600"},
        {"Cache-Control": "min-fresh=900, max-stale=0"},
        now=BASE + 100,
    )
    assert got.verdict == "FRESH"


def test_unparseable_min_fresh_is_ignored():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=600"},
        {"Cache-Control": "min-fresh=lots"},
        now=BASE + 100,
    )
    assert got.verdict == "FRESH"


def test_request_max_age_tightens_the_lifetime():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=600"},
        {"Cache-Control": "max-age=50"},
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 50
    assert got.verdict == "STALE"


def test_request_max_age_never_raises_the_lifetime():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=30"},
        {"Cache-Control": "max-age=600"},
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 30
    assert got.verdict == "STALE"


def test_request_max_age_tightens_a_heuristic_lifetime():
    got = ev(
        {"Date": http_date(BASE), "Last-Modified": http_date(BASE - 10000)},
        {"Cache-Control": "max-age=200"},
        now=BASE + 300,
    )
    assert got.freshness_lifetime == 200
    assert got.verdict == "STALE"


# --------------------------------------------------------------------------
# Cache-Control parsing
# --------------------------------------------------------------------------


def test_comma_inside_a_quoted_value_does_not_split_directives():
    # A naive split on "," turns the quoted list into a bare `no-store`.
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": 'max-age=600, ext="a,no-store,b"'},
        now=BASE + 100,
    )
    assert got.verdict == "FRESH"
    assert got.freshness_lifetime == 600


def test_quoted_numeric_value_is_still_numeric():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": 's-maxage="900", max-age=60'},
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 900
    assert got.verdict == "FRESH"


def test_last_duplicate_directive_wins():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "max-age=60, max-age=600"},
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 600
    assert got.verdict == "FRESH"


def test_empty_elements_and_padding_are_skipped():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": "  ,  max-age=600 ,, "},
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 600
    assert got.verdict == "FRESH"


def test_unparseable_numeric_directives_fall_through_to_expires():
    got = ev(
        {
            "Date": http_date(BASE),
            "Expires": http_date(BASE + 300),
            "Cache-Control": "s-maxage=soon, max-age=-5",
        },
        now=BASE + 100,
    )
    assert got.freshness_lifetime == 300
    assert got.verdict == "FRESH"


def test_no_cache_with_a_field_list_still_revalidates():
    got = ev(
        {"Date": http_date(BASE), "Cache-Control": 'no-cache="Set-Cookie", max-age=600'},
        now=BASE + 100,
    )
    assert got.verdict == "MUST_REVALIDATE"
    assert got.freshness_lifetime == 600


def test_directive_and_header_names_are_case_insensitive():
    got = ev(
        {"dAtE": http_date(BASE), "CACHE-CONTROL": "S-MaxAge=900, Must-Revalidate"},
        {"cache-CONTROL": "Max-Stale"},
        now=BASE + 100,
    )
    assert got.verdict == "MUST_REVALIDATE"
    assert got.freshness_lifetime == 900
    assert got.current_age == 100


def test_result_shape():
    got = ev({"Date": http_date(BASE), "Cache-Control": "max-age=600"}, now=BASE + 1)
    assert isinstance(got, Result)
    assert isinstance(got.current_age, int) and not isinstance(got.current_age, bool)
    assert isinstance(got.freshness_lifetime, int)
    assert got.verdict in {"FRESH", "STALE", "MUST_REVALIDATE"}


# --------------------------------------------------------------------------
# HTTP-date errors
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "Mon, 01 Jun 2026 12:00:00",           # no zone
        "Mon, 01 Jun 2026 12:00:00 UTC",       # right length, wrong zone
        "Monday, 01 Jun 2026 12:00:00 GMT",    # rfc850 style
        "Mon Jun  1 12:00:00 2026",            # asctime style
        "Mon, 1 Jun 2026 12:00:00 GMT",        # day not zero-padded
        "Mon, 01 JUN 2026 12:00:00 GMT",       # month not in canonical case
        "Xyz, 01 Jun 2026 12:00:00 GMT",       # not a day name
        "Mon, 01 Foo 2026 12:00:00 GMT",       # not a month name
        "Mon, 32 Jun 2026 12:00:00 GMT",       # no such day
        "Mon, 31 Jun 2026 12:00:00 GMT",       # June has 30 days
        "Mon, 01 Jun 2026 25:00:00 GMT",       # no such hour
        "Mon, 01 Jun 2026 12:60:00 GMT",       # no such minute
        "Mon, 01 Jun 2026 12-00-00 GMT",       # wrong time separators
        "1780315200",                          # epoch seconds
        "",
    ],
)
def test_malformed_date_raises_header_error(value):
    with pytest.raises(HeaderError):
        ev({"Date": value, "Cache-Control": "max-age=600"}, now=BASE + 100)


def test_malformed_expires_raises_header_error():
    with pytest.raises(HeaderError):
        ev({"Date": http_date(BASE), "Expires": "never"}, now=BASE + 100)


def test_malformed_last_modified_raises_header_error():
    with pytest.raises(HeaderError):
        ev({"Date": http_date(BASE), "Last-Modified": "0"}, now=BASE + 100)
