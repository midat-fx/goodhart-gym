"""The committed results still mean what the README says they mean."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gg import task as task_mod
from gg.verify import run_sealed


def _trials(run: str):
    return [json.loads(p.read_text()) for p in sorted((ROOT / "results" / run).rglob("*.json"))]


JULY_FAILURES = [r for r in _trials("2026-07") if not r["sealed_pass"]]


def test_the_july_failures_are_the_ones_the_readme_counts():
    assert len(JULY_FAILURES) == 11


@pytest.mark.parametrize(
    "trial", JULY_FAILURES, ids=[f"{r['model']}-{r['task']}-t{r['trial']}" for r in JULY_FAILURES]
)
def test_a_july_failure_still_fails_the_sealed_verifier(trial, tmp_path):
    """A softer verifier would explain a zero gap as well as better models would."""
    t = task_mod.load(trial["task"])
    workspace = task_mod.materialize(t, "null", tmp_path / "ws")
    for rel, text in trial["submission"].items():
        (workspace / rel).write_text(text)
    assert not run_sealed(t, workspace).passed
