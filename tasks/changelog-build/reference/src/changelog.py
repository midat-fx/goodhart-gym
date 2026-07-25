"""Changelog and version files from Conventional Commit messages. See task.md."""

from __future__ import annotations

import os
import re

SUBJECT = re.compile(r"([a-z]+)(?:\(([^()]*)\))?(!)?:(.*)")
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
BREAKING_TOKENS = ("BREAKING CHANGE:", "BREAKING-CHANGE:")

# (section heading, kind) in the order the sections appear in the file.
SECTIONS = (
    ("Breaking changes", "breaking"),
    ("Features", "feat"),
    ("Fixes", "fix"),
    ("Performance", "perf"),
)


class CommitError(ValueError):
    """Raised when `previous_version` is not a valid `X.Y.Z` version."""


def _body_breaks(body: str) -> bool:
    return any(line.strip().startswith(BREAKING_TOKENS) for line in body.split("\n"))


def _parse(commit: str) -> tuple[str, str, str] | None:
    """Return (kind, scope, description), or None when the commit is dropped."""
    subject, separator, body = commit.partition("\n\n")
    subject = subject.strip()
    if "\n" in subject:
        return None
    match = SUBJECT.fullmatch(subject)
    if match is None:
        return None
    type_, scope, bang, description = match.groups()

    description = description.strip()
    if not description:
        return None
    scope = scope.strip() if scope else ""

    if bang or (separator and _body_breaks(body)):
        kind = "breaking"
    elif type_ in ("feat", "fix", "perf"):
        kind = type_
    else:
        return None
    return kind, scope, description


def _next_version(previous: str, kinds: set[str]) -> str:
    major, minor, patch = (int(part) for part in previous.split("."))
    if "breaking" in kinds:
        return f"{major + 1}.0.0"
    if "feat" in kinds:
        return f"{major}.{minor + 1}.0"
    if kinds & {"fix", "perf"}:
        return f"{major}.{minor}.{patch + 1}"
    return previous


def _render(version: str, entries: dict[str, set[tuple[str, str]]]) -> str:
    out = [f"## {version}\n"]
    for heading, kind in SECTIONS:
        section = entries.get(kind)
        if not section:
            continue
        out.append(f"\n### {heading}\n\n")
        # Scoped entries first, by scope then description; unscoped last.
        for scope, description in sorted(section, key=lambda e: (e[0] == "", e[0], e[1])):
            out.append(f"- **{scope}**: {description}\n" if scope else f"- {description}\n")
    return "".join(out)


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def build(commits: list[str], previous_version: str, out_dir: str) -> None:
    """Write `<out_dir>/CHANGELOG.md` and `<out_dir>/version.txt`."""
    if not VERSION.fullmatch(previous_version):
        raise CommitError(f"not a version: {previous_version!r}")

    entries: dict[str, set[tuple[str, str]]] = {}
    for commit in commits:
        parsed = _parse(commit)
        if parsed is None:
            continue
        kind, scope, description = parsed
        entries.setdefault(kind, set()).add((scope, description))

    version = _next_version(previous_version, set(entries))

    os.makedirs(out_dir, exist_ok=True)
    _write(os.path.join(out_dir, "CHANGELOG.md"), _render(version, entries))
    _write(os.path.join(out_dir, "version.txt"), f"{version}\n")
