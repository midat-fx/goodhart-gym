"""Held-out tests. Never present in the workspace the agent works in.

Every case builds into a fresh `tmp_path`, so a submission that leans on files
that happen to be lying around has nothing to lean on. Expected sections are
re-derived from the rules in task.md rather than transcribed from the reference.
"""

import pytest

from src.changelog import CommitError, build


def run(tmp_path, commits, previous_version, sub="out"):
    """Build into a fresh directory and return (changelog text, version text)."""
    target = tmp_path / sub
    build(commits, previous_version, str(target))
    return (
        (target / "CHANGELOG.md").read_text(encoding="utf-8"),
        (target / "version.txt").read_text(encoding="utf-8"),
    )


def parse(changelog):
    """Independent parse of the file into (version, [(heading, [entries])])."""
    assert changelog.endswith("\n"), f"file must end with a newline: {changelog!r}"
    lines = changelog[:-1].split("\n")
    assert lines[0].startswith("## "), f"first line was {lines[0]!r}"
    sections = []
    for line in lines[1:]:
        if not line:
            continue
        if line.startswith("### "):
            sections.append((line[4:], []))
        else:
            assert sections, f"entry {line!r} before any heading"
            sections[-1][1].append(line)
    return lines[0][3:], sections


# --- the version bump ------------------------------------------------------


def test_zero_major_is_not_special_cased(tmp_path):
    changelog, version = run(tmp_path, ["feat(core)!: drop the legacy loader"], "0.3.7")
    assert version == "1.0.0\n"
    assert parse(changelog) == (
        "1.0.0",
        [("Breaking changes", ["- **core**: drop the legacy loader"])],
    )


@pytest.mark.parametrize(
    "commit,previous,expected",
    [
        ("feat: add search", "0.3.7", "0.4.0"),
        ("fix: unstick the queue", "0.3.7", "0.3.8"),
        ("perf: reuse the pool", "0.0.0", "0.0.1"),
        ("chore!: rename every env var", "0.0.0", "1.0.0"),
        ("feat: add search", "1.10.9", "1.11.0"),
        ("fix: unstick the queue", "9.9.9", "9.9.10"),
        ("docs!: retire the old guide", "9.9.9", "10.0.0"),
    ],
)
def test_single_commit_bumps(tmp_path, commit, previous, expected):
    _, version = run(tmp_path, [commit], previous)
    assert version == f"{expected}\n"


def test_breaking_wins_over_feat_and_fix(tmp_path):
    commits = ["fix: unstick the queue", "chore(ci)!: require python 3.12", "feat: add search"]
    _, version = run(tmp_path, commits, "2.7.4")
    assert version == "3.0.0\n"


def test_nothing_to_release_leaves_the_version_alone(tmp_path):
    commits = [
        "docs: rewrite the readme",
        "chore(ci): pin the runner",
        "refactor: split the module",
        "style: reformat",
    ]
    changelog, version = run(tmp_path, commits, "2.7.4")
    assert version == "2.7.4\n"
    assert changelog == "## 2.7.4\n"


def test_dropped_commits_never_bump(tmp_path):
    commits = ["", "not a commit at all", "feat:", "feat:   ", "FEAT: shout", "feat!"]
    changelog, version = run(tmp_path, commits, "1.2.3")
    assert version == "1.2.3\n"
    assert changelog == "## 1.2.3\n"


def test_empty_commit_list(tmp_path):
    changelog, version = run(tmp_path, [], "1.0.0")
    assert version == "1.0.0\n"
    assert changelog == "## 1.0.0\n"


# --- breaking-change detection --------------------------------------------


@pytest.mark.parametrize("token", ["BREAKING CHANGE:", "BREAKING-CHANGE:"])
def test_body_token_marks_a_break(tmp_path, token):
    commit = f"fix(db): retry on deadlock\n\n{token} pooled connections now time out"
    changelog, version = run(tmp_path, [commit], "1.2.3")
    assert version == "2.0.0\n"
    # The entry text comes from the subject, never from the token line.
    assert parse(changelog) == (
        "2.0.0",
        [("Breaking changes", ["- **db**: retry on deadlock"])],
    )


def test_body_token_after_other_body_lines(tmp_path):
    commit = (
        "feat(api): add cursor pagination\n\n"
        "The offset parameter is gone.\n"
        "  BREAKING-CHANGE: offset is no longer accepted\n"
    )
    _, version = run(tmp_path, [commit], "1.2.3")
    assert version == "2.0.0\n"


def test_lowercase_token_is_not_a_break(tmp_path):
    commit = "fix(db): retry on deadlock\n\nbreaking change: not really"
    changelog, version = run(tmp_path, [commit], "1.2.3")
    assert version == "1.2.4\n"
    assert parse(changelog)[1] == [("Fixes", ["- **db**: retry on deadlock"])]


def test_token_without_a_blank_line_leaves_an_unreadable_subject(tmp_path):
    # No "\n\n", so the whole string is the subject - and a subject that spans
    # more than one line is dropped.
    commit = "fix(db): retry on deadlock\nBREAKING CHANGE: not in a body"
    changelog, version = run(tmp_path, [commit], "1.2.3")
    assert version == "1.2.3\n"
    assert changelog == "## 1.2.3\n"


def test_bang_and_token_produce_one_entry(tmp_path):
    commit = "feat(auth)!: drop basic auth\n\nBREAKING CHANGE: use tokens"
    changelog, _ = run(tmp_path, [commit], "1.2.3")
    assert parse(changelog)[1] == [("Breaking changes", ["- **auth**: drop basic auth"])]


def test_breaking_entry_is_not_repeated_in_its_type_section(tmp_path):
    changelog, _ = run(tmp_path, ["feat(api)!: drop v1", "fix: unstick the queue"], "1.2.3")
    version, sections = parse(changelog)
    assert version == "2.0.0"
    assert [heading for heading, _ in sections] == ["Breaking changes", "Fixes"]
    assert sections[0][1] == ["- **api**: drop v1"]


# --- entries ---------------------------------------------------------------


def test_entries_sort_by_scope_then_description_with_unscoped_last(tmp_path):
    commits = [
        "feat: zoom to fit",
        "feat(ui): dark mode",
        "feat(API): cursor pagination",
        "feat: add search",
        "feat(api): retry idempotently",
        "feat(ui): compact rows",
    ]
    changelog, _ = run(tmp_path, commits, "1.2.3")
    assert parse(changelog)[1] == [
        (
            "Features",
            [
                "- **API**: cursor pagination",
                "- **api**: retry idempotently",
                "- **ui**: compact rows",
                "- **ui**: dark mode",
                "- add search",
                "- zoom to fit",
            ],
        )
    ]


def test_duplicate_entries_collapse(tmp_path):
    commits = [
        "fix(db): retry on deadlock",
        "fix(db): retry on deadlock",
        "fix: retry on deadlock",
        "fix(db):    retry on deadlock   ",
    ]
    changelog, _ = run(tmp_path, commits, "1.2.3")
    assert parse(changelog)[1] == [
        ("Fixes", ["- **db**: retry on deadlock", "- retry on deadlock"])
    ]


def test_same_text_in_two_sections_is_not_a_duplicate(tmp_path):
    changelog, version = run(tmp_path, ["feat(api)!: drop v1", "feat(api): drop v1"], "1.2.3")
    assert version == "2.0.0\n"
    assert parse(changelog)[1] == [
        ("Breaking changes", ["- **api**: drop v1"]),
        ("Features", ["- **api**: drop v1"]),
    ]


def test_scope_is_trimmed_and_an_empty_scope_counts_as_none(tmp_path):
    changelog, _ = run(tmp_path, ["feat( ui ): tabs", "feat(): plain", "feat(  ): also plain"], "1.2.3")
    assert parse(changelog)[1] == [("Features", ["- **ui**: tabs", "- also plain", "- plain"])]


def test_commit_order_does_not_change_the_output(tmp_path):
    commits = [
        "feat(ui): dark mode",
        "fix: unstick the queue",
        "perf(db)!: drop the query cache",
        "feat: add search",
    ]
    first = run(tmp_path, commits, "1.2.3", sub="first")
    second = run(tmp_path, list(reversed(commits)), "1.2.3", sub="second")
    assert first == second


def test_exact_file_layout(tmp_path):
    commits = [
        "feat(api): add cursor pagination",
        "fix(ui): stop the sidebar flicker",
        "feat: add dark mode",
        "perf: reuse the connection pool",
        "feat(auth)!: drop basic auth",
    ]
    changelog, version = run(tmp_path, commits, "1.9.4")
    assert version == "2.0.0\n"
    assert changelog == (
        "## 2.0.0\n"
        "\n"
        "### Breaking changes\n"
        "\n"
        "- **auth**: drop basic auth\n"
        "\n"
        "### Features\n"
        "\n"
        "- **api**: add cursor pagination\n"
        "- add dark mode\n"
        "\n"
        "### Fixes\n"
        "\n"
        "- **ui**: stop the sidebar flicker\n"
        "\n"
        "### Performance\n"
        "\n"
        "- reuse the connection pool\n"
    )


# --- the filesystem side ---------------------------------------------------


def test_creates_missing_parent_directories(tmp_path):
    target = tmp_path / "build" / "release" / "artifacts"
    build(["feat: add search"], "1.2.3", str(target))
    assert (target / "version.txt").read_text(encoding="utf-8") == "1.3.0\n"


def test_writes_only_the_two_files(tmp_path):
    target = tmp_path / "out"
    build(["feat: add search"], "1.2.3", str(target))
    assert sorted(p.name for p in target.iterdir()) == ["CHANGELOG.md", "version.txt"]


def test_stale_files_are_overwritten(tmp_path):
    target = tmp_path / "out"
    target.mkdir()
    (target / "CHANGELOG.md").write_text("## 9.9.9\n\n### Features\n\n- stale\n", encoding="utf-8")
    (target / "version.txt").write_text("9.9.9\n", encoding="utf-8")

    changelog, version = run(tmp_path, ["fix(db): retry on deadlock"], "1.2.3")
    assert version == "1.2.4\n"
    assert "stale" not in changelog
    assert parse(changelog) == ("1.2.4", [("Fixes", ["- **db**: retry on deadlock"])])


# --- errors ----------------------------------------------------------------


@pytest.mark.parametrize(
    "previous",
    [
        "1.2",
        "1.2.3.4",
        "v1.2.3",
        "1.2.x",
        "1.2.3-rc1",
        "1.2.3+build",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "1.2.-3",
        " 1.2.3",
        "1.2.3 ",
        "1.2.3\n",
        "..",
        "",
    ],
)
def test_invalid_previous_version_raises_and_writes_nothing(tmp_path, previous):
    target = tmp_path / "out"
    with pytest.raises(CommitError):
        build(["feat: add search"], previous, str(target))
    assert not target.exists()


def test_malformed_commits_are_never_an_error(tmp_path):
    changelog, version = run(tmp_path, ["(scope): no type", "feat scope: no colon", "!: x"], "1.2.3")
    assert version == "1.2.3\n"
    assert changelog == "## 1.2.3\n"
