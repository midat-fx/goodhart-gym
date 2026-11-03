"""Re-derive the sealed verdict of committed trials from their submissions.

A trial file stores the source the agent left behind. Rebuilding a pristine
workspace, writing that source over it and running the sealed verifier again
must give the verdict the file records; if it does not, the published numbers
no longer follow from the committed evidence.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import task as task_mod
from .verify import run_sealed


def rescore_trial(trial: dict) -> bool:
    """The sealed verdict the trial's stored submission earns today."""
    t = task_mod.load(trial["task"])
    with tempfile.TemporaryDirectory(prefix=f"gg-rescore-{t.slug}-") as tmp:
        workspace = task_mod.materialize(t, "null", Path(tmp) / "ws")
        for rel, text in trial["submission"].items():
            path = workspace / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return run_sealed(t, workspace).passed


def rescore(results_dir: Path) -> int:
    paths = sorted(results_dir.rglob("*.json"))
    if not paths:
        print(f"no trials under {results_dir}")
        return 1
    mismatches = 0
    for path in paths:
        trial = json.loads(path.read_text())
        now = rescore_trial(trial)
        if now != trial["sealed_pass"]:
            mismatches += 1
            print(f"MISMATCH {path}: stored sealed {trial['sealed_pass']}, rescored {now}")
    print(f"{len(paths) - mismatches}/{len(paths)} trials re-derive their sealed verdict")
    return 1 if mismatches else 0
