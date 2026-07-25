import json
import pathlib

import pytest

from src.freshness import HeaderError, evaluate

CASES = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "cases.json").read_text()
)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_case(case):
    got = evaluate(
        case["response_headers"],
        case["request_headers"],
        case["request_time"],
        case["response_time"],
        case["now"],
    )
    want = case["expected"]
    assert got.verdict == want["verdict"]
    assert got.current_age == want["current_age"]
    assert got.freshness_lifetime == want["freshness_lifetime"]


def test_malformed_date_raises():
    with pytest.raises(HeaderError):
        evaluate(
            {"Date": "yesterday", "Cache-Control": "max-age=600"},
            {},
            1780315200,
            1780315200,
            1780315300,
        )
