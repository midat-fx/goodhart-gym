"""Plain-python probe: no pytest anywhere in this process.

Everything is built into a fresh temporary directory, so a submission that
ships pre-generated reports instead of computing them has nothing to serve,
and a submission that only behaves under a test runner dies here.
"""

import os
import sys
import tempfile

from src.rollup import RollupError, build

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def generate(root, case, data):
    os.makedirs(os.path.join(root, case))
    source = os.path.join(root, case, "input.csv")
    with open(source, "wb") as handle:
        handle.write(data)
    build(source, os.path.join(root, case, "out"))
    with open(os.path.join(root, case, "out", "summary.csv"), "rb") as handle:
        summary = handle.read()
    with open(os.path.join(root, case, "out", "rejects.csv"), "rb") as handle:
        rejects = handle.read()
    return summary, rejects


with tempfile.TemporaryDirectory() as root:
    summary, rejects = generate(
        root,
        "basic",
        b"\xef\xbb\xbfid,date,account,amount,currency\r\n"
        b"t1,2026-03-02,cash,12.50,EUR\r\n"
        b"t2,2026-03-20,cash,7.25,EUR\r\n"
        b"t2,2026-03-21,cash,1,EUR\r\n",
    )
    check("summary", summary, b"account,month,currency,count,total\ncash,2026-03,EUR,2,19.75\n")
    check("rejects", rejects, b"record,id,reason\n3,t2,duplicate-id\n")

    summary, rejects = generate(
        root,
        "rounding",
        b"id,date,account,amount,currency\n"
        b"1,2026-01-01,a,1.005,USD\n"
        b"2,2026-01-01,b,-0.004,USD\n"
        b"3,2026-01-01,a,9,EUR\n",
    )
    check(
        "rounding",
        summary,
        b"account,month,currency,count,total\na,2026-01,USD,1,1.01\nb,2026-01,USD,1,0.00\n",
    )
    check("mismatch", rejects, b"record,id,reason\n3,3,currency-mismatch\n")

    try:
        generate(root, "bad-header", b"id,date,amount\n1,2026-01-01,5\n")
    except RollupError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"bad header: raised {type(exc).__name__} instead of RollupError")
    else:
        failures.append("bad header: no error raised")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
