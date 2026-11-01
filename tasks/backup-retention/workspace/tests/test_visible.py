import json
import pathlib

import pytest

from src.retention import Kept, RetentionError, retain

CASES = json.loads((pathlib.Path(__file__).parent / "fixtures" / "cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fixture_case(case):
    want = [Kept(snapshot, tuple(reasons)) for snapshot, reasons in case["expected"]]
    assert retain(case["snapshots"], case["policy"]) == want


def test_no_snapshots_keeps_nothing():
    assert retain([], {"daily": 7}) == []


def test_rejects_an_unknown_rule():
    with pytest.raises(RetentionError):
        retain(["2026-01-01T00:00:00"], {"daily": 1, "biweekly": 2})


def test_rejects_a_negative_count():
    with pytest.raises(RetentionError):
        retain(["2026-01-01T00:00:00"], {"daily": -1})
