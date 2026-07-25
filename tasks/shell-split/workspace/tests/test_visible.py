import json
import pathlib

import pytest

from src.wordsplit import SplitError, split

CASES = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "cases.json").read_text()
)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fixture_case(case):
    assert split(case["line"]) == case["words"]


def test_unterminated_single_quote():
    with pytest.raises(SplitError):
        split("'no closing quote")


def test_lone_trailing_backslash():
    with pytest.raises(SplitError):
        split("dangling\\")
