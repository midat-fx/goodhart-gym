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


def test_an_agent_that_never_ran_is_not_a_trial():
    from gg.agent import is_infra_error

    def trial(changed=(), **agent):
        base = {"timed_out": False, "num_turns": 3, "cost_usd": 0.2, "is_error": False}
        return {"agent": {**base, **agent}, "changed_files": list(changed)}

    # The CLI reported an error before any model call: an expired login.
    assert is_infra_error(trial(is_error=True, cost_usd=0, num_turns=1))
    # The CLI crashed before printing a result, or printed something else.
    assert is_infra_error(trial(num_turns=None, cost_usd=None, is_error=None))
    assert is_infra_error(
        trial(num_turns=None, cost_usd=None, is_error=None, parse_error="Traceback ...")
    )

    # Everything below is a trial, whatever its outcome.
    assert not is_infra_error(trial())
    assert not is_infra_error(trial(["src/a.py"], is_error=True, cost_usd=0.4))
    assert not is_infra_error(trial(timed_out=True, num_turns=None, cost_usd=None, is_error=None))
    assert not is_infra_error(trial(["src/a.py"], num_turns=None, cost_usd=None, is_error=None))


@pytest.mark.parametrize(
    "output, counts",
    [
        ("....\n4 passed in 0.02s\n", (4, 4)),
        ("F.\n1 failed, 1 passed in 0.03s\n", (1, 2)),
        ("E\n1 error in 0.05s\n", (0, 1)),
        ("==== 2 failed, 3 errors, 5 passed, 1 warning in 106.33s (0:01:46) ====\n", (5, 10)),
        ("timed out", (0, 0)),
        ("probe ok\n", (0, 0)),
        # A failing test that prints a tally of its own above the summary.
        ("F\n---- Captured stdout call ----\nbatch done: 7 passed\n1 failed in 0.01s\n", (0, 1)),
        ("F\nstep 3 passed in 2s\n1 failed in 0.01s\n", (0, 1)),
    ],
)
def test_counts_come_from_the_summary_line_only(output, counts):
    from gg.verify import Step

    assert Step("held-out tests", False, 1, output).counts == counts


def test_a_turn_budget_is_part_of_the_recorded_command(tmp_path):
    import json

    from gg.agent import agent_command, protocol_mismatch

    plain = agent_command("m", "<prompt>")
    budgeted = agent_command("m", "<prompt>", max_turns=5)
    assert "--max-turns" not in plain
    assert budgeted[-2:] == ["--max-turns", "5"] and budgeted[: len(plain)] == plain

    (tmp_path / "t-t1.json").write_text(json.dumps({"command": plain}))
    assert protocol_mismatch(tmp_path, plain) is None
    assert protocol_mismatch(tmp_path, budgeted) == tmp_path / "t-t1.json"
    assert protocol_mismatch(tmp_path / "missing", budgeted) is None


@pytest.mark.parametrize("run", ["2026-07", "2026-11"])
def test_the_committed_runs_used_todays_unbudgeted_command(run):
    """Changing agent_command silently would make new runs incomparable to these."""
    import json

    from gg.agent import agent_command

    root = Path(__file__).resolve().parent.parent / "results" / run
    for path in sorted(root.rglob("*.json")):
        trial = json.loads(path.read_text())
        assert trial["command"] == agent_command(trial["model"], "<prompt>"), path
