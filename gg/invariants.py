"""The deterministic proof that every claim in this repo holds.

For each task, three kinds of candidate are built from files in the repo and
put through both verifiers. The expected matrix is:

    null        naive FAIL   sealed FAIL   (doing nothing is never a pass)
    reference   naive PASS   sealed PASS   (an honest solution passes both)
    exploit     naive PASS   sealed FAIL   (the gap this benchmark measures)

Nothing here calls a model. `gg invariants` is the whole evidence base, and it
runs in CI on every push.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import task as task_mod
from .task import Task
from .verify import run_naive, run_sealed


@dataclass
class Check:
    task: str
    variant: str
    hack_class: str
    expected: tuple[bool, bool]
    actual: tuple[bool, bool]
    detail: str = ""
    caught_by: str = ""
    dropped: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.expected == self.actual

    def as_dict(self) -> dict:
        return {
            "task": self.task,
            "variant": self.variant,
            "class": self.hack_class,
            "expected": {"naive": self.expected[0], "sealed": self.expected[1]},
            "actual": {"naive": self.actual[0], "sealed": self.actual[1]},
            "ok": self.ok,
            "caught_by": self.caught_by,
            "dropped": list(self.dropped),
            "detail": self.detail,
        }


def _check(t: Task, variant: str, expected: tuple[bool, bool], hack_class: str) -> Check:
    with tempfile.TemporaryDirectory(prefix="gg-inv-") as tmp:
        candidate = task_mod.materialize(t, variant, Path(tmp) / "candidate")
        naive = run_naive(t, candidate)
        sealed = run_sealed(t, candidate)

    actual = (naive.passed, sealed.passed)
    detail = ""
    if actual != expected:
        if naive.passed != expected[0]:
            detail = f"naive: {naive.failure_summary or 'passed unexpectedly'}"
        else:
            detail = f"sealed: {sealed.failure_summary or 'passed unexpectedly'}"

    # Which layer of the sealed verifier actually did the work.
    caught_by = ""
    if variant.startswith("exploit:") and not sealed.passed:
        first_failed = next(s.name for s in sealed.steps if not s.passed)
        caught_by = first_failed
        if sealed.dropped and first_failed == "pristine visible tests":
            caught_by = "submission allowlist"

    return Check(
        t.slug, variant, hack_class, expected, actual, detail, caught_by, tuple(sealed.dropped)
    )


def check_task(t: Task) -> list[Check]:
    checks = [
        _check(t, "null", (False, False), "—"),
        _check(t, "reference", (True, True), "—"),
    ]
    for exploit in t.exploits:
        checks.append(
            _check(t, f"exploit:{exploit.name}", (True, False), exploit.hack_class)
        )
    return checks


def check_all(slugs: list[str] | None = None) -> list[Check]:
    tasks = [task_mod.load(s) for s in slugs] if slugs else task_mod.all_tasks()
    out: list[Check] = []
    for t in tasks:
        out.extend(check_task(t))
    return out
