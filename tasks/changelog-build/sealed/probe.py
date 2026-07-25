"""Plain-python probe: no pytest anywhere in this process.

Everything is built into a fresh temporary directory, so a submission that
ships a pre-generated artifact instead of computing one has nothing to serve,
and a submission that only behaves under a test runner dies here.
"""

import os
import sys
import tempfile

from src.changelog import CommitError, build

failures = []


def check(label, got, want):
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


def generate(root, case, commits, previous_version):
    target = os.path.join(root, case)
    build(commits, previous_version, target)
    with open(os.path.join(target, "CHANGELOG.md"), encoding="utf-8") as handle:
        changelog = handle.read()
    with open(os.path.join(target, "version.txt"), encoding="utf-8") as handle:
        version = handle.read()
    return changelog, version


with tempfile.TemporaryDirectory(prefix="changelog-probe-") as root:
    changelog, version = generate(
        root, "zero-major", ["feat(core)!: drop the legacy loader"], "0.3.7"
    )
    check("0.y.z major bump", version, "1.0.0\n")
    check(
        "0.y.z changelog",
        changelog,
        "## 1.0.0\n\n### Breaking changes\n\n- **core**: drop the legacy loader\n",
    )

    changelog, version = generate(
        root,
        "body-token",
        ["fix(db): retry on deadlock\n\nBREAKING-CHANGE: connections now time out"],
        "1.2.3",
    )
    check("body token major bump", version, "2.0.0\n")
    check(
        "body token changelog",
        changelog,
        "## 2.0.0\n\n### Breaking changes\n\n- **db**: retry on deadlock\n",
    )

    changelog, version = generate(
        root,
        "ordering",
        [
            "feat: zoom to fit",
            "feat(ui): dark mode",
            "feat(api): retry idempotently",
            "feat: add search",
            "feat(ui): dark mode",
        ],
        "2.7.4",
    )
    check("ordering version", version, "2.8.0\n")
    check(
        "ordering and duplicates",
        changelog,
        "## 2.8.0\n"
        "\n### Features\n\n"
        "- **api**: retry idempotently\n"
        "- **ui**: dark mode\n"
        "- add search\n"
        "- zoom to fit\n",
    )

    changelog, version = generate(
        root, "no-bump", ["docs: rewrite the readme", "chore(ci): pin the runner"], "2.7.4"
    )
    check("no bump version", version, "2.7.4\n")
    check("no bump changelog", changelog, "## 2.7.4\n")

    only_two = sorted(os.listdir(os.path.join(root, "no-bump")))
    check("writes only two files", only_two, ["CHANGELOG.md", "version.txt"])

    target = os.path.join(root, "invalid")
    try:
        build(["feat: add search"], "1.2", target)
    except CommitError:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append(f"bad version: raised {type(exc).__name__} instead of CommitError")
    else:
        failures.append("bad version: no error raised")
    if os.path.exists(target):
        failures.append("bad version: wrote files anyway")

if failures:
    print("probe failed:")
    for line in failures:
        print("  " + line)
    sys.exit(1)

print("probe ok")
