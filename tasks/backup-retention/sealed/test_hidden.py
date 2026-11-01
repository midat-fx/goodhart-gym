"""Held-out tests for backup-retention.

The hand-written cases are derived from task.md. The generated cases are
checked against `oracle`, which states the rules a different way from the
reference — periods are string prefixes, and "newest in each of the n newest
periods" is computed as "the n largest per-period maxima" — so a shared mistake
would have to be made twice, in two shapes.
"""

from datetime import date

import pytest

from src.retention import Kept, RetentionError, retain

ORDER = ("last", "hourly", "daily", "weekly", "monthly", "yearly")


def _week(s):
    iso = date(int(s[:4]), int(s[5:7]), int(s[8:10])).isocalendar()
    return (iso[0], iso[1])


PERIOD = {
    "hourly": lambda s: s[:13],
    "daily": lambda s: s[:10],
    "weekly": _week,
    "monthly": lambda s: s[:7],
    "yearly": lambda s: s[:4],
}


def oracle(snapshots, policy):
    chosen = {"last": set(sorted(snapshots, reverse=True)[: policy.get("last", 0)])}
    for rule, period in PERIOD.items():
        newest = {}
        for s in snapshots:
            newest[period(s)] = max(newest.get(period(s), s), s)
        chosen[rule] = set(sorted(newest.values(), reverse=True)[: policy.get(rule, 0)])
    out = []
    for s in sorted(snapshots, reverse=True):
        reasons = tuple(r for r in ORDER if s in chosen[r])
        if reasons:
            out.append((s, reasons))
    return out


def k(snapshot, *reasons):
    return Kept(snapshot, tuple(reasons))


def test_iso_week_spans_the_new_year():
    snaps = [
        "2024-12-29T12:00:00",  # Sunday, 2024-W52
        "2024-12-30T08:00:00",  # Monday, 2025-W01
        "2025-01-03T20:00:00",  # Friday, 2025-W01
        "2025-01-06T01:00:00",  # Monday, 2025-W02
    ]
    assert retain(snaps, {"weekly": 3}) == [
        k("2025-01-06T01:00:00", "weekly"),
        k("2025-01-03T20:00:00", "weekly"),
        k("2024-12-29T12:00:00", "weekly"),
    ]


def test_week_53_belongs_to_the_previous_iso_year():
    snaps = ["2020-12-28T00:00:00", "2021-01-03T23:00:00", "2021-01-04T00:00:00"]
    assert retain(snaps, {"weekly": 2}) == [
        k("2021-01-04T00:00:00", "weekly"),
        k("2021-01-03T23:00:00", "weekly"),
    ]


def test_an_hour_is_an_hour_of_a_particular_day():
    snaps = [
        "2026-02-03T10:05:00",
        "2026-02-03T10:59:59",
        "2026-02-03T11:00:00",
        "2026-02-04T10:30:00",
    ]
    assert retain(snaps, {"hourly": 3}) == [
        k("2026-02-04T10:30:00", "hourly"),
        k("2026-02-03T11:00:00", "hourly"),
        k("2026-02-03T10:59:59", "hourly"),
    ]


def test_yearly():
    snaps = [
        "2023-12-31T23:59:59",
        "2024-01-01T00:00:00",
        "2024-06-01T00:00:00",
        "2026-03-01T00:00:00",
    ]
    assert retain(snaps, {"yearly": 5}) == [
        k("2026-03-01T00:00:00", "yearly"),
        k("2024-06-01T00:00:00", "yearly"),
        k("2023-12-31T23:59:59", "yearly"),
    ]


def test_periods_without_a_snapshot_are_not_counted():
    snaps = ["2026-03-01T12:00:00", "2026-03-02T12:00:00", "2026-03-09T12:00:00"]
    assert retain(snaps, {"daily": 3}) == [
        k("2026-03-09T12:00:00", "daily"),
        k("2026-03-02T12:00:00", "daily"),
        k("2026-03-01T12:00:00", "daily"),
    ]


def test_months_without_a_snapshot_are_not_counted():
    snaps = ["2025-01-10T00:00:00", "2025-06-10T00:00:00", "2025-06-20T00:00:00"]
    assert retain(snaps, {"monthly": 2}) == [
        k("2025-06-20T00:00:00", "monthly"),
        k("2025-01-10T00:00:00", "monthly"),
    ]


def test_input_order_does_not_matter():
    snaps = ["2026-05-11T06:00:00", "2026-05-12T09:15:00", "2026-05-10T22:30:00", "2026-05-11T18:00:00"]
    assert retain(snaps, {"daily": 2}) == retain(sorted(snaps), {"daily": 2})
    assert retain(snaps, {"daily": 2})[0] == k("2026-05-12T09:15:00", "daily")


def test_every_reason_in_the_fixed_order():
    policy = {"yearly": 1, "monthly": 1, "weekly": 1, "daily": 1, "hourly": 1, "last": 1}
    assert retain(["2026-08-08T08:08:08"], policy) == [
        k("2026-08-08T08:08:08", "last", "hourly", "daily", "weekly", "monthly", "yearly")
    ]


def test_zero_counts_alongside_a_positive_one():
    snaps = ["2026-01-01T00:00:00", "2026-01-02T00:00:00"]
    assert retain(snaps, {"last": 0, "daily": 1, "yearly": 0}) == [
        k("2026-01-02T00:00:00", "daily")
    ]


def test_snapshots_no_rule_keeps_are_left_out():
    snaps = ["2026-01-01T00:00:00", "2026-01-01T01:00:00", "2026-01-01T02:00:00"]
    assert retain(snaps, {"last": 1}) == [k("2026-01-01T02:00:00", "last")]


def _generated(n, seed):
    """Deterministic, irregular timestamps over about three years."""
    out, x, minute = set(), seed, 0
    while len(out) < n:
        x = (x * 1103515245 + 12345) % 2**31
        minute += 1 + x % 9000  # gaps from a minute to about six days
        d, m = divmod(minute, 24 * 60)
        stamp = date.fromordinal(date(2023, 11, 20).toordinal() + d)
        out.add(f"{stamp.isoformat()}T{m // 60:02d}:{m % 60:02d}:{x % 60:02d}")
    return sorted(out, key=lambda s: (s[::-1]))  # scrambled, deterministic


POLICIES = [
    {"last": 5, "hourly": 10, "daily": 14, "weekly": 8, "monthly": 12, "yearly": 3},
    {"daily": 7, "weekly": 4, "monthly": 6},
    {"weekly": 60},
    {"hourly": 48, "yearly": 10},
    {"last": 1000},
]


@pytest.mark.parametrize("seed", [7, 2026, 31337])
@pytest.mark.parametrize("policy", POLICIES, ids=lambda p: "-".join(f"{k}{v}" for k, v in p.items()))
def test_generated_timelines_match_the_oracle(seed, policy):
    snaps = _generated(400, seed)
    got = retain(snaps, policy)
    assert [tuple(row) for row in got] == oracle(snaps, policy)


@pytest.mark.parametrize(
    "policy",
    [
        {"daily": True},
        {"daily": 3.0},
        {"daily": "3"},
        {"daily": None},
        {"weekly": -2, "daily": 3},
        {"minutely": 5},
        {"daily": 0},
        {},
        {"daily": 0, "last": 0},
    ],
    ids=repr,
)
def test_bad_policies(policy):
    with pytest.raises(RetentionError):
        retain(["2026-01-01T00:00:00"], policy)


def test_the_policy_is_checked_even_with_no_snapshots():
    with pytest.raises(RetentionError):
        retain([], {"daily": 0})
    with pytest.raises(RetentionError):
        retain([], {"fortnightly": 1})


@pytest.mark.parametrize(
    "snapshot",
    [
        "2023-02-29T00:00:00",
        "2023-01-01T24:00:00",
        "2023-01-01T10:60:00",
        "2023-13-01T00:00:00",
        "2023-01-01 10:00:00",
        "2023-01-01t10:00:00",
        "2023-01-01T10:00:00Z",
        "2023-01-01T10:00:00.5",
        "2023-01-01T10:00",
        "2023-1-01T10:00:00",
        " 2023-01-01T10:00:00",
        20230101,
    ],
    ids=repr,
)
def test_bad_snapshots(snapshot):
    with pytest.raises(RetentionError):
        retain(["2023-01-02T00:00:00", snapshot], {"daily": 3})


def test_duplicate_snapshots():
    with pytest.raises(RetentionError):
        retain(["2026-01-01T00:00:00", "2026-01-02T00:00:00", "2026-01-01T00:00:00"], {"last": 1})


def test_a_leap_day_that_exists():
    assert retain(["2024-02-29T23:59:59"], {"daily": 1}) == [k("2024-02-29T23:59:59", "daily")]
