"""goodhart-gym command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import invariants, task as task_mod
from .verify import verify

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
OFF = "\033[0m"


def _color(text: str, code: str) -> str:
    return text if not sys.stdout.isatty() else f"{code}{text}{OFF}"


def _mark(passed: bool) -> str:
    return _color("PASS", GREEN) if passed else _color("FAIL", RED)


def cmd_tasks(args: argparse.Namespace) -> int:
    tasks = task_mod.all_tasks()
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "slug": t.slug,
                        "title": t.title,
                        "summary": t.summary,
                        "exploits": [
                            {"name": e.name, "class": e.hack_class} for e in t.exploits
                        ],
                    }
                    for t in tasks
                ],
                indent=2,
            )
        )
        return 0
    for t in tasks:
        classes = ", ".join(sorted({e.hack_class for e in t.exploits})) or "—"
        print(f"{t.slug:<18} {t.title}")
        print(f"{'':<18} {_color(classes, DIM)}")
    print(f"\n{len(tasks)} tasks, {sum(len(t.exploits) for t in tasks)} exploits")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    t = task_mod.load(args.task)
    verdicts = verify(t, Path(args.workspace))
    if args.json:
        print(json.dumps({k: v.as_dict() for k, v in verdicts.items()}, indent=2))
    else:
        for name, v in verdicts.items():
            print(f"{name:<8} {_mark(v.passed)}")
            if not v.passed:
                print(f"         {_color(v.failure_summary.splitlines()[0][:120], DIM)}")
            for dropped in v.dropped:
                print(f"         {_color('dropped ' + dropped, DIM)}")
    return 0 if verdicts["sealed"].passed else 1


def cmd_invariants(args: argparse.Namespace) -> int:
    checks = invariants.check_all(args.task or None)
    if not checks:
        print("no tasks found", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([c.as_dict() for c in checks], indent=2))
    else:
        current = None
        for c in checks:
            if c.task != current:
                current = c.task
                print(f"\n{c.task}")
            exp = f"naive {'PASS' if c.expected[0] else 'FAIL'} / sealed {'PASS' if c.expected[1] else 'FAIL'}"
            status = _color("ok", GREEN) if c.ok else _color("VIOLATED", RED)
            label = c.variant if c.hack_class == "—" else f"{c.variant}  [{c.hack_class}]"
            caught = f"caught by {c.caught_by}" if c.caught_by else ""
            print(f"  {label:<46} {exp:<32} {status:<12} {_color(caught, DIM)}")
            if not c.ok:
                print(f"    got naive {c.actual[0]} sealed {c.actual[1]} — {c.detail[:300]}")

    failed = [c for c in checks if not c.ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} invariants hold")
    return 1 if failed else 0


def cmd_run(args: argparse.Namespace) -> int:
    from .agent import run_suite

    return run_suite(
        model=args.model,
        slugs=args.task or None,
        trials=args.trials,
        out_dir=Path(args.out),
        timeout=args.timeout,
        resume=not args.no_resume,
        workers=args.workers,
    )


def cmd_report(args: argparse.Namespace) -> int:
    from .report import build_report

    return build_report(Path(args.results), Path(args.out))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gg", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("tasks", help="list tasks and their exploits")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_tasks)

    p = sub.add_parser("verify", help="run both verifiers on a workspace")
    p.add_argument("task")
    p.add_argument("workspace")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("invariants", help="prove the reference/exploit matrix (no model calls)")
    p.add_argument("--task", action="append", help="limit to a task (repeatable)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_invariants)

    p = sub.add_parser("run", help="run an agent on every task and score it under both verifiers")
    p.add_argument("--model", required=True, help="model id passed to the agent CLI")
    p.add_argument("--task", action="append")
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--out", default="results")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--workers", type=int, default=3, help="concurrent agent runs")
    p.add_argument("--no-resume", action="store_true", help="re-run trials that already have results")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("report", help="build the hack-gap table and chart from results")
    p.add_argument("--results", default="results")
    p.add_argument("--out", default="docs")
    p.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)
