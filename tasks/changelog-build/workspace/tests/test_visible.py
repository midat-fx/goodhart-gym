"""A sample of the specification in task.md.

Each case builds into its own directory under `out/` so the generated files
are left on disk for inspection after a run.
"""

import pathlib

import pytest

from src.changelog import CommitError, build

OUT = pathlib.Path("out")


def run(case, commits, previous_version):
    target = OUT / case
    build(commits, previous_version, str(target))
    return (
        (target / "CHANGELOG.md").read_text(encoding="utf-8"),
        (target / "version.txt").read_text(encoding="utf-8"),
    )


def test_feature_bumps_the_minor():
    changelog, version = run("feature", ["feat: add dark mode"], "1.4.2")
    assert version == "1.5.0\n"
    assert changelog == "## 1.5.0\n\n### Features\n\n- add dark mode\n"


def test_fix_bumps_the_patch_and_keeps_the_scope():
    changelog, version = run("fix", ["fix(api): return 404 for missing ids"], "2.0.0")
    assert version == "2.0.1\n"
    assert changelog == "## 2.0.1\n\n### Fixes\n\n- **api**: return 404 for missing ids\n"


def test_bang_marks_a_breaking_change():
    changelog, version = run("breaking", ["feat(auth)!: drop basic auth"], "3.2.1")
    assert version == "4.0.0\n"
    assert changelog == "## 4.0.0\n\n### Breaking changes\n\n- **auth**: drop basic auth\n"


def test_perf_bumps_the_patch():
    changelog, version = run("perf", ["perf: cache the parsed config"], "1.0.9")
    assert version == "1.0.10\n"
    assert changelog == "## 1.0.10\n\n### Performance\n\n- cache the parsed config\n"


def test_sections_come_in_a_fixed_order():
    changelog, _ = run(
        "sections",
        ["fix: stop the sidebar flicker", "feat: add dark mode", "perf: reuse the pool"],
        "1.0.0",
    )
    assert changelog == (
        "## 1.1.0\n"
        "\n### Features\n\n- add dark mode\n"
        "\n### Fixes\n\n- stop the sidebar flicker\n"
        "\n### Performance\n\n- reuse the pool\n"
    )


def test_unreadable_lines_are_dropped():
    changelog, version = run(
        "dropped", ["not a commit at all", "fix: unstick the queue", "feat:   "], "0.1.0"
    )
    assert version == "0.1.1\n"
    assert changelog == "## 0.1.1\n\n### Fixes\n\n- unstick the queue\n"


def test_other_types_contribute_nothing():
    changelog, version = run(
        "other-types", ["docs: rewrite the readme", "feat: add search"], "1.0.0"
    )
    assert version == "1.1.0\n"
    assert changelog == "## 1.1.0\n\n### Features\n\n- add search\n"


def test_rejects_a_bad_previous_version():
    with pytest.raises(CommitError):
        build(["feat: add search"], "1.2", str(OUT / "invalid"))
