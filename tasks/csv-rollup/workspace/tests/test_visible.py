"""A sample of the specification in task.md.

Each case writes its input under `out/<case>/` and builds into the same
directory, so the generated files are left on disk for inspection after a run.
"""

import pathlib

import pytest

from src.rollup import RollupError, build

OUT = pathlib.Path("out")
HEADER = "id,date,account,amount,currency\n"


def run(case, text):
    target = OUT / case
    target.mkdir(parents=True, exist_ok=True)
    source = target / "input.csv"
    source.write_text(text, encoding="utf-8")
    build(str(source), str(target))
    return (
        (target / "summary.csv").read_bytes().decode("utf-8"),
        (target / "rejects.csv").read_bytes().decode("utf-8"),
    )


def test_one_account_one_month():
    summary, rejects = run(
        "one-month",
        HEADER + "t1,2026-03-02,cash,12.50,EUR\nt2,2026-03-20,cash,7.25,EUR\n",
    )
    assert summary == "account,month,currency,count,total\ncash,2026-03,EUR,2,19.75\n"
    assert rejects == "record,id,reason\n"


def test_rows_sorted_by_account_then_month():
    summary, _ = run(
        "sorted",
        HEADER
        + "t1,2026-04-01,savings,100,USD\n"
        + "t2,2026-03-15,cash,-4.10,USD\n"
        + "t3,2026-02-28,savings,50.5,USD\n",
    )
    assert summary == (
        "account,month,currency,count,total\n"
        "cash,2026-03,USD,1,-4.10\n"
        "savings,2026-02,USD,1,50.50\n"
        "savings,2026-04,USD,1,100.00\n"
    )


def test_a_repeated_id_is_rejected():
    summary, rejects = run(
        "duplicate",
        HEADER + "t1,2026-01-05,cash,10,GBP\nt1,2026-01-06,cash,99,GBP\n",
    )
    assert summary == "account,month,currency,count,total\ncash,2026-01,GBP,1,10.00\n"
    assert rejects == "record,id,reason\n2,t1,duplicate-id\n"


def test_a_bad_amount_is_malformed():
    _, rejects = run(
        "bad-amount",
        HEADER + "t1,2026-01-05,cash,1.2.3,GBP\nt2,2026-01-06,cash,5,GBP\n",
    )
    assert rejects == "record,id,reason\n1,t1,malformed\n"


def test_header_only_still_writes_both_files():
    summary, rejects = run("empty", HEADER)
    assert summary == "account,month,currency,count,total\n"
    assert rejects == "record,id,reason\n"


def test_a_missing_column_is_an_error():
    with pytest.raises(RollupError):
        run("no-currency", "id,date,account,amount\nt1,2026-01-01,cash,5\n")
