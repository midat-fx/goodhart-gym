"""Monthly per-account totals from a CSV of transactions. See task.md."""

from __future__ import annotations


class RollupError(ValueError):
    """Raised for an input file that cannot be rolled up at all."""


def build(input_csv: str, out_dir: str) -> None:
    """Read `input_csv`; write `<out_dir>/summary.csv` and `<out_dir>/rejects.csv`."""
    raise NotImplementedError
