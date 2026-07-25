"""Task discovery and workspace materialization."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"


@dataclass(frozen=True)
class Exploit:
    name: str
    hack_class: str
    note: str
    files_dir: Path


@dataclass(frozen=True)
class Task:
    slug: str
    title: str
    summary: str
    submission: tuple[str, ...]
    root: Path

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def sealed(self) -> Path:
        return self.root / "sealed"

    @property
    def reference(self) -> Path:
        return self.root / "reference"

    @property
    def prompt(self) -> str:
        return (self.root / "task.md").read_text()

    @property
    def exploits(self) -> list[Exploit]:
        out = []
        exploits_dir = self.root / "exploits"
        if not exploits_dir.is_dir():
            return out
        for d in sorted(p for p in exploits_dir.iterdir() if p.is_dir()):
            meta = json.loads((d / "meta.json").read_text())
            out.append(
                Exploit(
                    name=d.name,
                    hack_class=meta["class"],
                    note=meta["note"],
                    files_dir=d / "files",
                )
            )
        return out


def load(slug: str) -> Task:
    root = TASKS_DIR / slug
    meta = json.loads((root / "meta.json").read_text())
    return Task(
        slug=slug,
        title=meta["title"],
        summary=meta["summary"],
        submission=tuple(meta["submission"]),
        root=root,
    )


def all_tasks() -> list[Task]:
    if not TASKS_DIR.is_dir():
        return []
    return [load(p.name) for p in sorted(TASKS_DIR.iterdir()) if (p / "meta.json").is_file()]


def _overlay(src: Path, dest: Path) -> None:
    """Copy every file under src over dest, creating parents as needed."""
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        target = dest / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def materialize(task: Task, variant: str, dest: Path) -> Path:
    """Build a candidate workspace.

    variant is "null" (untouched stub), "reference", or "exploit:<name>".
    """
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(task.workspace, dest)

    if variant == "null":
        pass
    elif variant == "reference":
        _overlay(task.reference, dest)
    elif variant.startswith("exploit:"):
        name = variant.split(":", 1)[1]
        matches = [e for e in task.exploits if e.name == name]
        if not matches:
            raise KeyError(f"{task.slug}: no exploit named {name!r}")
        _overlay(matches[0].files_dir, dest)
    else:
        raise ValueError(f"unknown variant {variant!r}")

    return dest
