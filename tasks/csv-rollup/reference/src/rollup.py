"""Monthly per-account totals from a CSV of transactions. See task.md."""

from __future__ import annotations

import csv
import os
import re
from datetime import date


class RollupError(ValueError):
    """Raised for an input file that cannot be rolled up at all."""


REQUIRED = ("id", "date", "account", "amount", "currency")
DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")
AMOUNT = re.compile(r"-?[0-9]+(\.[0-9]{1,4})?")
CURRENCY = re.compile(r"[A-Z]{3}")


def _is_date(text: str) -> bool:
    match = DATE.fullmatch(text)
    if not match:
        return False
    try:
        date(*map(int, match.groups()))
    except ValueError:
        return False
    return True


def _well_formed(row: dict[str, str]) -> bool:
    return (
        row["id"] != ""
        and row["account"] != ""
        and _is_date(row["date"])
        and AMOUNT.fullmatch(row["amount"]) is not None
        and CURRENCY.fullmatch(row["currency"]) is not None
    )


def _units(amount: str) -> int:
    """An amount as an exact integer number of ten-thousandths."""
    whole, _, frac = amount.lstrip("-").partition(".")
    units = int(whole) * 10_000 + int(frac.ljust(4, "0"))
    return -units if amount.startswith("-") else units


def _money(units: int) -> str:
    """Ten-thousandths to cents, halves away from zero, never "-0.00"."""
    cents, rest = divmod(abs(units), 100)
    if rest >= 50:
        cents += 1
    sign = "-" if units < 0 and cents else ""
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def _write(path: str, header: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def build(input_csv: str, out_dir: str) -> None:
    """Read `input_csv`; write `<out_dir>/summary.csv` and `<out_dir>/rejects.csv`."""
    with open(input_csv, encoding="utf-8-sig", newline="") as handle:
        records = [r for r in csv.reader(handle) if r]

    if not records:
        raise RollupError("no header record")
    header = records[0]
    if len(set(header)) != len(header):
        raise RollupError(f"duplicate column in header {header!r}")
    missing = [name for name in REQUIRED if name not in header]
    if missing:
        raise RollupError(f"header lacks {missing}")
    where = {name: header.index(name) for name in REQUIRED}

    taken_ids: set[str] = set()
    currency_of: dict[str, str] = {}
    totals: dict[tuple[str, str], list[int]] = {}
    rejects: list[list[str]] = []

    for number, fields in enumerate(records[1:], start=1):
        if len(fields) != len(header):
            id_index = where["id"]
            rejects.append([str(number), fields[id_index] if id_index < len(fields) else "", "malformed"])
            continue
        row = {name: fields[i] for name, i in where.items()}
        if not _well_formed(row):
            reason = "malformed"
        elif row["id"] in taken_ids:
            reason = "duplicate-id"
        elif currency_of.get(row["account"], row["currency"]) != row["currency"]:
            reason = "currency-mismatch"
        else:
            reason = ""
        if reason:
            rejects.append([str(number), row["id"], reason])
            continue

        taken_ids.add(row["id"])
        currency_of.setdefault(row["account"], row["currency"])
        slot = totals.setdefault((row["account"], row["date"][:7]), [0, 0])
        slot[0] += 1
        slot[1] += _units(row["amount"])

    summary = [
        [account, month, currency_of[account], str(count), _money(total)]
        for (account, month), (count, total) in sorted(totals.items())
    ]

    os.makedirs(out_dir, exist_ok=True)
    _write(os.path.join(out_dir, "summary.csv"), ["account", "month", "currency", "count", "total"], summary)
    _write(os.path.join(out_dir, "rejects.csv"), ["record", "id", "reason"], rejects)
