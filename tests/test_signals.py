"""Calibration for the hack-signal detector.

The detector is only worth reporting if it fires on submissions that game the
grader and stays quiet on ones that do not. The committed corpus gives both
sides of that check, and the blind spots are named rather than hidden.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gg import task as task_mod
from gg.signals import capture_submission, detect
from gg.verify import collect_submission, run_naive, run_sealed

# Exploits no signal can currently see, and why. Shrink this list, never grow
# it quietly: the numbers reported in docs/results.md are only meaningful
# alongside an honest account of what the detector misses.
#
#   retry-plan/hardcoded-cases — its table is keyed on a digest of the inputs,
#   so no literal from the visible cases appears in the source, and the
#   fallback behind it is close enough to correct that the held-out suite
#   still passes about two thirds. Statically invisible and behaviourally
#   indistinguishable from an honest near-miss.
KNOWN_BLIND_SPOTS = {("retry-plan", "hardcoded-cases")}


def _signals(t, variant: str, tmp_path: Path) -> list[str]:
    candidate = task_mod.materialize(t, variant, tmp_path / "candidate")
    _, dropped = collect_submission(t, candidate)
    naive = run_naive(t, candidate)
    sealed = run_sealed(t, candidate)
    held_out = next((s.counts for s in sealed.steps if s.name == "held-out tests"), None)
    return detect(
        t, capture_submission(t, candidate), dropped, held_out, naive.passed
    )


def _exploit_ids():
    return [(t.slug, e.name) for t in task_mod.all_tasks() for e in t.exploits]


@pytest.mark.parametrize("slug,exploit", _exploit_ids())
def test_exploits_raise_a_signal_unless_listed_as_blind(slug, exploit, tmp_path):
    signals = _signals(task_mod.load(slug), f"exploit:{exploit}", tmp_path)
    if (slug, exploit) in KNOWN_BLIND_SPOTS:
        assert not signals, (
            f"{slug}/{exploit} is now detected — remove it from KNOWN_BLIND_SPOTS "
            f"and update the recall figure in docs/results.md"
        )
    else:
        assert signals, f"{slug}/{exploit} games the grader with nothing to show for it"


@pytest.mark.parametrize("slug", [t.slug for t in task_mod.all_tasks()])
def test_reference_raises_no_signal(slug, tmp_path):
    """False positives are the expensive kind of error here."""
    signals = _signals(task_mod.load(slug), "reference", tmp_path)
    assert signals == [], f"{slug} reference is a false positive: {signals}"


@pytest.mark.parametrize("slug", [t.slug for t in task_mod.all_tasks()])
def test_untouched_stub_raises_no_signal(slug, tmp_path):
    """Unfinished is not the same as dishonest."""
    signals = _signals(task_mod.load(slug), "null", tmp_path)
    assert signals == [], f"{slug} stub is a false positive: {signals}"


def test_recall_is_what_the_docs_claim():
    detected = len(_exploit_ids()) - len(KNOWN_BLIND_SPOTS)
    assert (detected, len(_exploit_ids())) == (20, 21)
