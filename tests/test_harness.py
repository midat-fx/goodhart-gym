"""Tests for the harness itself. The task matrix is proved by `gg invariants`."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gg import task as task_mod
from gg.verify import DENIED_NAMES, _accepted, collect_submission

HACK_CLASSES = {
    "test-gaming",
    "verifier-tampering",
    "hardcoding",
    "fixture-inspection",
    "output-forgery",
    "env-sniffing",
}


def tasks():
    return task_mod.all_tasks()


def test_there_are_tasks():
    assert tasks(), "no tasks found"


@pytest.mark.parametrize("slug", [t.slug for t in tasks()])
def test_task_layout(slug):
    t = task_mod.load(slug)
    assert (t.root / "task.md").is_file()
    assert (t.workspace / "conftest.py").is_file()
    assert (t.workspace / "tests").is_dir()
    assert t.reference.is_dir() and any(t.reference.rglob("*.py"))
    assert (t.sealed / "test_hidden.py").is_file()
    assert (t.sealed / "probe.py").is_file()
    assert t.exploits, "a task with no exploit measures nothing"


@pytest.mark.parametrize("slug", [t.slug for t in tasks()])
def test_stub_refuses_to_work(slug):
    """The null candidate must be a failure, so a no-op can never score."""
    t = task_mod.load(slug)
    sources = list((t.workspace / "src").glob("*.py"))
    body = "\n".join(p.read_text() for p in sources)
    assert "NotImplementedError" in body


@pytest.mark.parametrize("slug", [t.slug for t in tasks()])
def test_exploit_classes_are_known(slug):
    for exploit in task_mod.load(slug).exploits:
        assert exploit.hack_class in HACK_CLASSES, exploit.hack_class
        assert exploit.note.strip(), "an exploit without a note is undocumented"
        assert exploit.files_dir.is_dir()


@pytest.mark.parametrize("slug", [t.slug for t in tasks()])
def test_sealed_material_never_leaks_into_the_workspace(slug):
    """Held-out tests and probes must not be reachable while the agent works."""
    t = task_mod.load(slug)
    workspace_files = {p.name for p in t.workspace.rglob("*") if p.is_file()}
    assert "test_hidden.py" not in workspace_files
    assert "probe.py" not in workspace_files


def test_every_hack_class_has_at_least_one_exploit():
    covered = {e.hack_class for t in tasks() for e in t.exploits}
    assert covered == HACK_CLASSES, f"missing: {sorted(HACK_CLASSES - covered)}"


def test_allowlist_refuses_files_that_change_how_tests_run():
    t = tasks()[0]
    for name in DENIED_NAMES:
        assert not _accepted(t, Path("src") / name), name
    assert not _accepted(t, Path("src/evil.pth"))
    assert _accepted(t, Path("src/anything.py"))


def test_allowlist_refuses_files_outside_the_submission():
    t = tasks()[0]
    assert not _accepted(t, Path("tests/test_visible.py"))
    assert not _accepted(t, Path("conftest.py"))
    assert not _accepted(t, Path("out/report.json"))


def test_modified_scaffolding_is_reported_and_dropped(tmp_path):
    t = tasks()[0]
    candidate = task_mod.materialize(t, "null", tmp_path / "candidate")
    (candidate / "tests" / "test_visible.py").write_text("def test_ok():\n    pass\n")
    (candidate / "conftest.py").write_text("# replaced\n")
    (candidate / "src" / "extra.py").write_text("VALUE = 1\n")

    accepted, dropped = collect_submission(t, candidate)

    assert Path("src/extra.py") in accepted
    joined = " ".join(dropped)
    assert "tests/test_visible.py" in joined
    assert "conftest.py" in joined


def test_untouched_scaffolding_is_not_reported(tmp_path):
    t = tasks()[0]
    candidate = task_mod.materialize(t, "null", tmp_path / "candidate")
    _, dropped = collect_submission(t, candidate)
    assert dropped == []
