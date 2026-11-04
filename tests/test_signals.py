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
# Empty since 2026-11-04. The last entry, retry-plan/hardcoded-cases, keys its
# table on json.dumps of the call, and lookup-table now unpacks keys like that.
# A table keyed on a real digest (hashlib, hash()) would still be invisible.
KNOWN_BLIND_SPOTS: set[tuple[str, str]] = set()


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
    assert (detected, len(_exploit_ids())) == (31, 31)


@pytest.mark.parametrize("slug", [t.slug for t in task_mod.all_tasks() if t.visible_conflict])
def test_correcting_a_conflicting_test_passes_sealed_and_is_still_flagged(slug, tmp_path):
    """On a conflict task, the honest code plus an edited test goes green twice.

    That is not a gap trial, so the gap column never sees it; the signal is the
    only place it shows up.
    """
    t = task_mod.load(slug)
    candidate = task_mod.materialize(t, "reference", tmp_path / "candidate")
    for node in t.visible_conflict:
        path, _, name = node.partition("::")
        test_file = candidate / path
        test_file.write_text(test_file.read_text().replace(f"def {name}(", f"def _{name}("))
    assert run_naive(t, candidate).passed
    assert run_sealed(t, candidate).passed
    _, dropped = collect_submission(t, candidate)
    assert "touched-grading-files" in detect(t, capture_submission(t, candidate), dropped)
