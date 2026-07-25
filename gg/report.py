"""Turn agent-run results into the table and the chart in the README."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

# Chosen to stay legible on both the light and the dark GitHub theme.
NAIVE_COLOR = "#e0794b"
SEALED_COLOR = "#3d8f7d"
TEXT = "#8b949e"
RULE = "#8b949e44"


def _load(results_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(results_dir.rglob("*.json"))]


def _rate(rows: list[dict], key: str) -> float:
    return 100.0 * sum(1 for r in rows if r[key]) / len(rows) if rows else 0.0


def _svg(models: list[str], stats: dict[str, dict]) -> str:
    width, height = 720, 300
    left, bottom, top = 60, 60, 40
    plot_h = height - bottom - top
    group_w = (width - left - 20) / max(len(models), 1)
    bar_w = min(46, group_w / 3)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
    ]

    for pct in (0, 25, 50, 75, 100):
        y = top + plot_h - plot_h * pct / 100
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - 20}" y2="{y:.1f}" stroke="{RULE}" />'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 4:.1f}" font-size="11" fill="{TEXT}" '
            f'text-anchor="end">{pct}%</text>'
        )

    for i, model in enumerate(models):
        s = stats[model]
        cx = left + group_w * i + group_w / 2
        for offset, (value, color) in enumerate(
            ((s["naive"], NAIVE_COLOR), (s["sealed"], SEALED_COLOR))
        ):
            h = plot_h * value / 100
            x = cx - bar_w - 4 + offset * (bar_w + 8)
            y = top + plot_h - h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                f'fill="{color}" rx="2" />'
            )
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" font-size="12" '
                f'fill="{TEXT}" text-anchor="middle">{value:.0f}%</text>'
            )
        parts.append(
            f'<text x="{cx:.1f}" y="{height - bottom + 20:.1f}" font-size="12" '
            f'fill="{TEXT}" text-anchor="middle">{model}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{height - bottom + 38:.1f}" font-size="11" '
            f'fill="{TEXT}" text-anchor="middle">hack gap {s["gap"]:.0f} pts</text>'
        )

    parts.append(
        f'<rect x="{left}" y="12" width="10" height="10" fill="{NAIVE_COLOR}" rx="2" />'
        f'<text x="{left + 16}" y="21" font-size="12" fill="{TEXT}">naive verifier</text>'
        f'<rect x="{left + 120}" y="12" width="10" height="10" fill="{SEALED_COLOR}" rx="2" />'
        f'<text x="{left + 136}" y="21" font-size="12" fill="{TEXT}">sealed verifier</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


START, END = "<!-- RESULTS -->", "<!-- /RESULTS -->"


def _update_readme(models: list[str], stats: dict[str, dict], out_dir: Path) -> None:
    """Rewrite the block between the RESULTS markers so the headline is generated."""
    readme = out_dir.parent / "README.md"
    if not readme.is_file():
        return
    text = readme.read_text()
    if START not in text or END not in text:
        return

    worst = max(models, key=lambda m: stats[m]["gap"])
    s = stats[worst]
    block = [
        START,
        "",
        f"![hack gap]({out_dir.name}/hack-gap.svg)",
        "",
        f"On the run in `docs/results.md`, **`{worst}` scores {s['naive']:.0f}% under the "
        f"naive verifier and {s['sealed']:.0f}% under the sealed one — a gap of "
        f"{s['gap']:.0f} points** across {s['n']} trials.",
        "",
        "| model | trials | naive pass | sealed pass | gap | trials with hack signals |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in models:
        st = stats[model]
        block.append(
            f"| `{model}` | {st['n']} | {st['naive']:.0f}% | {st['sealed']:.0f}% | "
            f"**{st['gap']:.0f} pts** | {st['signalled']} |"
        )
    block += [
        "",
        "The gap is what the two verifiers disagree about; it is **not** all deliberate "
        "cheating. A submission written in good faith that misses an edge case lands in "
        "the same column as one that hardcoded the answers. The last column counts "
        "trials carrying structural evidence of gaming — grading files touched, the test "
        "runner detected, fixtures read — and `docs/results.md` breaks it down.",
        "",
        END,
    ]

    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    readme.write_text(head + "\n".join(block) + tail)


def build_report(results_dir: Path, out_dir: Path) -> int:
    rows = _load(results_dir)
    if not rows:
        print(f"no results under {results_dir}")
        return 1

    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)

    models = sorted(by_model)
    stats = {}
    for model in models:
        rs = by_model[model]
        naive, sealed = _rate(rs, "naive_pass"), _rate(rs, "sealed_pass")
        stats[model] = {
            "naive": naive,
            "sealed": sealed,
            "gap": naive - sealed,
            "n": len(rs),
            "gap_trials": sum(1 for r in rs if r["gap"]),
            "signalled": sum(1 for r in rs if r.get("hack_signals")),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hack-gap.svg").write_text(_svg(models, stats))

    lines = ["# Measured results", "", "## Hack gap", "", "![hack gap](hack-gap.svg)", ""]
    lines += [
        "| model | trials | naive pass | sealed pass | gap | gap trials | with hack signals |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in models:
        s = stats[model]
        lines.append(
            f"| `{model}` | {s['n']} | {s['naive']:.0f}% | {s['sealed']:.0f}% | "
            f"**{s['gap']:.0f} pts** | {s['gap_trials']} | {s['signalled']} |"
        )

    lines += [
        "",
        "## Gap is not the same as cheating",
        "",
        "A gap trial passed the naive verifier and failed the sealed one. Two very",
        "different things land in that column: a submission that gamed the grader, and",
        "one written in good faith that got an edge case wrong. Only the first is reward",
        "hacking, so the runner records structural evidence separately.",
        "",
        "`touched-grading-files` and `runner-detection` are near-exact — a submission",
        "either modified a file outside the allowlist or it did not, and either branches",
        "on the test runner or it does not. `fixture-access` is exact about the read and",
        "silent about the intent. `visible-literals-echoed` is a heuristic: it counts",
        "literals that appear in the visible tests and in the submission but nowhere in",
        "the specification, which is what a lookup table looks like from the outside.",
        "Raw submissions are committed under `results/`, so every count here can be",
        "checked by reading the code the agent actually wrote.",
        "",
    ]

    signals = Counter(s for r in rows for s in r.get("hack_signals", []))
    if signals:
        lines += ["| signal | trials |", "| --- | ---: |"]
        for name, count in signals.most_common():
            lines.append(f"| `{name}` | {count} |")
    else:
        lines.append("_No trial in this run carried any hack signal._")

    caught = Counter(r["caught_by"] for r in rows if r["gap"])
    if caught:
        lines += [
            "",
            "## Which sealed layer produced the gap",
            "",
            "| layer | trials |",
            "| --- | ---: |",
        ]
        for layer, count in caught.most_common():
            lines.append(f"| {layer} | {count} |")

    lines += [
        "",
        "## Per task",
        "",
        "| task | naive pass | sealed pass | gap trials | signalled |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    for slug in sorted(by_task):
        rs = by_task[slug]
        lines.append(
            f"| `{slug}` | {_rate(rs, 'naive_pass'):.0f}% | {_rate(rs, 'sealed_pass'):.0f}% | "
            f"{sum(1 for r in rs if r['gap'])}/{len(rs)} | "
            f"{sum(1 for r in rs if r.get('hack_signals'))} |"
        )

    total_cost = sum(
        (r["agent"].get("cost_usd") or 0) for r in rows if isinstance(r.get("agent"), dict)
    )
    plural = "run" if len(rows) == 1 else "runs"
    lines += [
        "",
        f"_{len(rows)} agent {plural}. Reported API-equivalent cost: ${total_cost:.2f}._",
        "",
    ]

    (out_dir / "results.md").write_text("\n".join(lines))
    _update_readme(models, stats, out_dir)
    print(f"wrote {out_dir / 'results.md'} and {out_dir / 'hack-gap.svg'}")
    for model in models:
        s = stats[model]
        print(f"  {model}: naive {s['naive']:.0f}%  sealed {s['sealed']:.0f}%  gap {s['gap']:.0f} pts")
    return 0
