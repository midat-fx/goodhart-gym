"""The committed results still mean what the README says they mean."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gg.rescore import rescore, rescore_trial


def _trials(run: str):
    return [json.loads(p.read_text()) for p in sorted((ROOT / "results" / run).rglob("*.json"))]


JULY_FAILURES = [r for r in _trials("2026-07") if not r["sealed_pass"]]


def test_the_july_failures_are_the_ones_the_readme_counts():
    assert len(JULY_FAILURES) == 11


@pytest.mark.parametrize(
    "trial", JULY_FAILURES, ids=[f"{r['model']}-{r['task']}-t{r['trial']}" for r in JULY_FAILURES]
)
def test_a_july_failure_still_fails_the_sealed_verifier(trial):
    """A softer verifier would explain a zero gap as well as better models would."""
    assert not rescore_trial(trial)


def test_rescore_reports_a_trial_whose_stored_verdict_is_wrong(tmp_path, capsys):
    honest, forged = dict(JULY_FAILURES[0]), dict(JULY_FAILURES[0], sealed_pass=True)
    (tmp_path / "honest.json").write_text(json.dumps(honest))
    assert rescore(tmp_path) == 0
    (tmp_path / "forged.json").write_text(json.dumps(forged))
    assert rescore(tmp_path) == 1
    out = capsys.readouterr().out
    assert "MISMATCH" in out and "forged.json" in out and "1/2 trials" in out
