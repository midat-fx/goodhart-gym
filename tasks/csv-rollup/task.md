# csv-rollup

Implement `build` in `src/rollup.py`.

```python
def build(input_csv: str, out_dir: str) -> None
```

Read a CSV file of transactions at the path `input_csv` and write two files into
the directory `out_dir`: `summary.csv`, with one total per account per month,
and `rejects.csv`, listing every record that could not be used and why. Create
`out_dir` (and its parents) if it does not exist, and overwrite both files if
they do. Both files are always written, even when they have no rows.

## Reading the input

The input is UTF-8 and may begin with a byte-order mark, which is not part of
the first column name. It follows RFC 4180: fields are separated by commas, a
field may be enclosed in double quotes, a quoted field may contain commas, line
breaks and doubled double quotes (`""` stands for one `"`), and records end with
either `\n` or `\r\n`.

The first record is the header. It must contain each of the column names `id`,
`date`, `account`, `amount` and `currency`, exactly as written here. Columns may
come in any order, and any other columns are allowed and ignored. A completely
empty line is not a record: it is skipped and not counted.

Every record after the header gets a **record number**, starting at `1` for the
first one after the header.

## Which records are used

Records are taken in file order. Each record is either **accepted** or
**rejected** with exactly one reason, the first of these that applies:

1. `malformed` — the record does not have the same number of fields as the
   header, or any of these is false:
   - `id` is not empty;
   - `account` is not empty;
   - `date` is `YYYY-MM-DD` in ASCII digits and is a real calendar date;
   - `amount` is an optional `-`, one or more ASCII digits, and optionally a `.`
     followed by one to four ASCII digits — nothing else: no `+`, no spaces, no
     thousands separators, no exponent, no leading or trailing `.`;
   - `currency` is exactly three upper-case ASCII letters.
2. `duplicate-id` — an earlier **accepted** record has the same `id`.
3. `currency-mismatch` — an earlier **accepted** record for the same `account`
   has a different `currency`. An account's currency is the currency of its
   first accepted record.

Field values are used exactly as they appear, without trimming whitespace. A
rejected record has no effect on later ones: its `id` is not taken, and it does
not set its account's currency.

## summary.csv

Header `account,month,currency,count,total`, then one row for every `(account,
month)` that has at least one accepted record, where `month` is the `YYYY-MM` of
the record's `date`. Rows are sorted by `account`, then by `month`, comparing
strings by code point.

- `currency` is the account's currency.
- `count` is the number of accepted records in that account and month.
- `total` is the **exact** sum of their amounts, then rounded to two decimal
  places with halves rounded **away from zero**: `0.125` becomes `0.13` and
  `-0.125` becomes `-0.13`. It is always written with exactly two decimal places
  and no exponent or `+` sign. A total that rounds to zero is written `0.00`,
  never `-0.00`.

## rejects.csv

Header `record,id,reason`, then one row for every rejected record, in record
number order. `id` is the record's `id` field exactly as given, which may be
empty. If the record has no `id` field at all (it is too short), write an empty
`id`.

## Writing the output

Both files are UTF-8 without a byte-order mark. Every line, including the last,
ends with a single `\n` — not `\r\n`. A field is enclosed in double quotes only
when it contains a comma, a double quote, a `\r` or a `\n`, and a double quote
inside a quoted field is doubled.

## Errors

Raise `RollupError` (already defined in `src/rollup.py`) when the input has no
header record at all, when the header lacks one of the five required columns, or
when a column name appears more than once in the header (an empty name counts
as a name, so a header with two empty columns is refused). In those cases no
output files need to be written.

## What you have

`tests/test_visible.py` holds a small suite. Each test writes its input under
`out/<case>/` and builds into the same directory, so the generated files are left
on disk for inspection. Run it with `python -m pytest tests`. It does not cover
the whole specification above — the specification is the contract, not the test
file.
