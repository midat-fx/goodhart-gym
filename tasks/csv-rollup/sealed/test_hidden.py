"""Held-out tests for csv-rollup.

Every expected file is written out by hand from the rules in task.md. Inputs are
written as bytes so that byte-order marks and line endings are exactly what the
case says they are.
"""

import pytest

from src.rollup import RollupError, build

HEADER = "id,date,account,amount,currency\r\n"
SUMMARY = "account,month,currency,count,total\n"
REJECTS = "record,id,reason\n"


def run(tmp_path, data, out="out"):
    source = tmp_path / "input.csv"
    source.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    target = tmp_path / out
    build(str(source), str(target))
    return (
        (target / "summary.csv").read_bytes().decode("utf-8"),
        (target / "rejects.csv").read_bytes().decode("utf-8"),
    )


def rows(*lines):
    return HEADER + "".join(line + "\r\n" for line in lines)


def test_halves_round_away_from_zero(tmp_path):
    summary, _ = run(
        tmp_path,
        rows(
            "1,2026-01-01,a,0.125,EUR",
            "2,2026-01-01,b,-0.125,EUR",
            "3,2026-01-01,c,2.675,EUR",
            "4,2026-01-01,d,1.005,EUR",
            "5,2026-01-01,e,0.0049,EUR",
            "6,2026-01-01,f,0.0050,EUR",
        ),
    )
    assert summary == SUMMARY + (
        "a,2026-01,EUR,1,0.13\n"
        "b,2026-01,EUR,1,-0.13\n"
        "c,2026-01,EUR,1,2.68\n"
        "d,2026-01,EUR,1,1.01\n"
        "e,2026-01,EUR,1,0.00\n"
        "f,2026-01,EUR,1,0.01\n"
    )


def test_the_sum_is_exact_before_rounding(tmp_path):
    summary, _ = run(
        tmp_path,
        rows(
            "1,2026-05-01,a,0.0025,USD",
            "2,2026-05-02,a,0.0025,USD",
            "3,2026-05-03,b,98765432109876543210.0050,USD",
            "4,2026-05-04,c,0.1,USD",
            "5,2026-05-05,c,0.2,USD",
        ),
    )
    assert summary == SUMMARY + (
        "a,2026-05,USD,2,0.01\n"
        "b,2026-05,USD,1,98765432109876543210.01\n"
        "c,2026-05,USD,2,0.30\n"
    )


def test_a_total_that_rounds_to_zero_has_no_sign(tmp_path):
    summary, _ = run(
        tmp_path,
        rows(
            "1,2026-01-01,a,-0.004,EUR",
            "2,2026-01-01,b,1.00,EUR",
            "3,2026-01-02,b,-1.00,EUR",
            "4,2026-01-01,c,-0,EUR",
        ),
    )
    assert summary == SUMMARY + (
        "a,2026-01,EUR,1,0.00\n"
        "b,2026-01,EUR,2,0.00\n"
        "c,2026-01,EUR,1,0.00\n"
    )


def test_a_byte_order_mark_is_not_part_of_the_first_column(tmp_path):
    summary, _ = run(tmp_path, b"\xef\xbb\xbf" + rows("1,2026-02-01,a,3,EUR").encode())
    assert summary == SUMMARY + "a,2026-02,EUR,1,3.00\n"


def test_lf_and_crlf_input_give_the_same_lf_output(tmp_path):
    crlf = rows("1,2026-02-01,a,3,EUR", "2,2026-02-01,a,x,EUR")
    lf = crlf.replace("\r\n", "\n")
    a = run(tmp_path, crlf, "crlf")
    b = run(tmp_path, lf, "lf")
    assert a == b == (SUMMARY + "a,2026-02,EUR,1,3.00\n", REJECTS + "2,2,malformed\n")


def test_columns_in_any_order_and_extra_columns(tmp_path):
    data = (
        "currency,memo,amount,id,account,date\n"
        "EUR,coffee,3.20,t1,cash,2026-06-01\n"
        "EUR,,1.80,t2,cash,2026-06-09\n"
    )
    summary, _ = run(tmp_path, data)
    assert summary == SUMMARY + "cash,2026-06,EUR,2,5.00\n"


def test_quoted_fields_in_and_out(tmp_path):
    data = (
        "id,date,account,amount,currency,memo\n"
        '1,2026-07-01,"Smith, J.",10,EUR,"two\nlines"\n'
        '2,2026-07-02,"say ""hi""",5,EUR,plain\n'
        '3,2026-07-03,"line\nbreak",1,EUR,x\n'
        '"4,5",2026-07-04,bad,1.2.3,EUR,x\n'
    )
    summary, rejects = run(tmp_path, data)
    assert summary == SUMMARY + (
        '"Smith, J.",2026-07,EUR,1,10.00\n'
        '"line\nbreak",2026-07,EUR,1,1.00\n'
        '"say ""hi""",2026-07,EUR,1,5.00\n'
    )
    assert rejects == REJECTS + '4,"4,5",malformed\n'


def test_currency_mismatch_and_a_rejected_id_is_not_taken(tmp_path):
    summary, rejects = run(
        tmp_path,
        rows(
            "1,2026-01-01,cash,10,EUR",
            "2,2026-01-02,cash,20,USD",
            "2,2026-01-03,cash,30,EUR",
        ),
    )
    assert summary == SUMMARY + "cash,2026-01,EUR,2,40.00\n"
    assert rejects == REJECTS + "2,2,currency-mismatch\n"


def test_a_rejected_record_does_not_set_the_currency(tmp_path):
    summary, rejects = run(
        tmp_path,
        rows(
            "1,2026-02-30,acct,10,USD",
            "2,2026-03-01,acct,10,EUR",
            "3,2026-03-02,acct,10,EUR",
        ),
    )
    assert summary == SUMMARY + "acct,2026-03,EUR,2,20.00\n"
    assert rejects == REJECTS + "1,1,malformed\n"


def test_reasons_are_checked_in_order(tmp_path):
    _, rejects = run(
        tmp_path,
        rows(
            "1,2026-01-01,cash,10,EUR",
            "1,2026-01-01,cash,oops,EUR",  # duplicate and malformed: malformed
            "1,2026-01-01,cash,10,USD",  # duplicate and mismatch: duplicate-id
            "2,2026-01-01,cash,10,USD",  # mismatch only
        ),
    )
    assert rejects == REJECTS + "2,1,malformed\n3,1,duplicate-id\n4,2,currency-mismatch\n"


def test_blank_lines_are_skipped_and_not_numbered(tmp_path):
    data = "\n" + HEADER + "\r\n1,2026-01-01,a,1,EUR\r\n\r\n\n2,2026-01-01,a,bad,EUR\r\n\r\n"
    summary, rejects = run(tmp_path, data)
    assert summary == SUMMARY + "a,2026-01,EUR,1,1.00\n"
    assert rejects == REJECTS + "2,2,malformed\n"


def test_wrong_field_counts_are_malformed(tmp_path):
    data = (
        "date,account,amount,currency,id\n"
        "2026-01-01,a,1,EUR\n"  # too short: no id field at all
        "2026-01-01,a,1,EUR,t2,extra\n"  # too long
        "2026-01-01,a,1,EUR,t3\n"
    )
    summary, rejects = run(tmp_path, data)
    assert summary == SUMMARY + "a,2026-01,EUR,1,1.00\n"
    assert rejects == REJECTS + "1,,malformed\n2,t2,malformed\n"


@pytest.mark.parametrize(
    "line",
    [
        "x,2026-01-01,a,+5,EUR",
        "x,2026-01-01,a, 5,EUR",
        "x,2026-01-01,a,5 ,EUR",
        "x,2026-01-01,a,5.,EUR",
        "x,2026-01-01,a,.5,EUR",
        "x,2026-01-01,a,1e3,EUR",
        'x,2026-01-01,a,"1,000",EUR',
        "x,2026-01-01,a,5.12345,EUR",
        "x,2026-01-01,a,--5,EUR",
        "x,2026-01-01,a,５,EUR",
        "x,2026-01-01,a,,EUR",
        "x,2026-02-30,a,5,EUR",
        "x,2026-2-03,a,5,EUR",
        "x,2026/02/03,a,5,EUR",
        "x,2026-02-03T00:00,a,5,EUR",
        "x,2026-01-01,a,5,eur",
        "x,2026-01-01,a,5,EURO",
        "x,2026-01-01,a,5,EU",
        ",2026-01-01,a,5,EUR",
        "x,2026-01-01,,5,EUR",
        "x,2026-01-01,a,5,EUR ",
    ],
)
def test_malformed_fields(tmp_path, line):
    summary, rejects = run(tmp_path, rows(line))
    assert summary == SUMMARY
    want_id = line.split(",")[0]
    assert rejects == REJECTS + f"1,{want_id},malformed\n"


def test_whitespace_is_part_of_the_value(tmp_path):
    summary, _ = run(tmp_path, rows("1,2026-01-01, cash,1,EUR", "2,2026-01-01,cash,2,EUR"))
    assert summary == SUMMARY + " cash,2026-01,EUR,1,1.00\ncash,2026-01,EUR,1,2.00\n"


def test_sorted_by_code_point(tmp_path):
    summary, _ = run(
        tmp_path,
        rows(
            "1,2026-03-01,alpha,1,EUR",
            "2,2026-01-01,Ärger,1,EUR",
            "3,2026-02-01,Zeta,1,EUR",
            "4,2025-12-01,alpha,1,EUR",
        ),
    )
    assert summary == SUMMARY + (
        "Zeta,2026-02,EUR,1,1.00\n"
        "alpha,2025-12,EUR,1,1.00\n"
        "alpha,2026-03,EUR,1,1.00\n"
        "Ärger,2026-01,EUR,1,1.00\n"
    )


def test_output_directory_is_created_and_files_overwritten(tmp_path):
    target = tmp_path / "deep" / "er"
    target.mkdir(parents=True)
    (target / "summary.csv").write_text("stale\n")
    (target / "rejects.csv").write_text("stale\n")
    summary, rejects = run(tmp_path, rows("1,2026-01-01,a,1,EUR"), out="deep/er")
    assert summary == SUMMARY + "a,2026-01,EUR,1,1.00\n"
    assert rejects == REJECTS
    summary, _ = run(tmp_path, rows("1,2026-01-01,a,1,EUR"), out="new/nested/dir")
    assert summary == SUMMARY + "a,2026-01,EUR,1,1.00\n"


def test_output_has_no_byte_order_mark(tmp_path):
    run(tmp_path, b"\xef\xbb\xbf" + rows("1,2026-01-01,a,1,EUR").encode())
    assert not (tmp_path / "out" / "summary.csv").read_bytes().startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\xef\xbb\xbf",
        b"\n\n\r\n",
        b"id,date,account,amount,currency,id\n",
        b"id,date,account,amount,Currency\n",
    ],
    ids=["empty", "bom-only", "blank-lines", "duplicate-column", "case-matters"],
)
def test_unusable_headers(tmp_path, data):
    with pytest.raises(RollupError):
        run(tmp_path, data)
