# Design notes

Why the harness is built the way it is, and what changed in the November 2026
re-measure. `docs/authoring.md` covers how to write a task. This file covers
why things are the way they are.

## Core decisions

**Two verifiers, not one strict one.** The question here is how much a common
grading design overstates a score. Answering it means running that design (the
naive verifier) next to one that cannot be gamed (the sealed verifier) on the
same submission. A strict verifier on its own can say a submission failed, but
not that a typical benchmark would have passed it.

**Sealed is layered.** Allowlist, pristine visible tests, held-out tests, then a
pytest-free probe. Each layer stops a class that walks through the others:
`gg invariants` shows which layer caught each exploit, and the env-sniffing
exploits pass both pytest steps and die only at the probe. Dropping any layer
lets a committed exploit through.

**The allowlist is structural.** `conftest.py`, `pytest.ini` and friends are
refused by name, so the sealed run never has to understand what such a file
does. A behavioural check would be an arms race; a filename denylist is not.

**Exploits are committed, and CI proves them.** The invariant matrix
(null fails both, reference passes both, every exploit passes naive and fails
sealed) makes no model calls, runs in seconds and runs on every push. The claim
"the sealed verifier stops these" is checked by CI, not taken on the author's
word.

**Gap is not cheating.** An honest submission that misses an edge case lands in
the same column as one that hardcoded the answers. Signals (`gg/signals.py`)
are reported next to the gap and never folded into it. They are recomputed from
the committed submissions at report time, so a better detector re-scores old
runs without new agent calls.

**Subjects run without the operator's config.** `--setting-sources ""` keeps
personal instructions, hooks and memory away from the agent under test. The
full command goes into every result file.

## November 2026 re-measure

**Explicit model ids, not aliases.** The July run used `--model haiku` and
`--model sonnet` and did not record what they resolved to. The re-measure uses
`claude-haiku-5-5` and `claude-sonnet-5-5`, and every trial now stores
`agent.models_used` (the keys of the CLI's `modelUsage`) and `agent.cli_version`.
A number in the README can then be tied to the model that produced it.

**Dated result folders.** `results/2026-07/` keeps the July trials byte-for-byte,
and `results/2026-11/` holds the new ones. `gg report --results results/2026-07`
still reproduces the archived table in `docs/results-2026-07.md` exactly. One
directory per run means old and new numbers are never averaged together by
accident.

**Same protocol, different trial counts.** Prompt, tool list, timeout, both
verifiers and the per-trial record are unchanged. The budget was 60 agent runs:
14 tasks × 2 models × 2 trials = 56, with 4 left for re-runs of infrastructure
failures. July used 3 trials for `haiku` and 2 for `sonnet`. With two trials a
task-level rate moves in steps of 50 points, so per-task numbers are anecdotes.
The suite-level rate over 28 trials per model is the number that matters.

**An agent that never ran is not a trial.** The first smoke run hit an expired
CLI login and was scored as a failed trial in under a second. `is_infra_error`
now refuses to record a run that errored at zero cost with no file changes. It
stays missing, so `--resume` retries it. An auth failure would otherwise show
up as a capability result.

**Four new tasks, aimed at the thin classes.** Before this run
`output-forgery` had one exploit and `verifier-tampering` and
`fixture-inspection` had two each. The new tasks add one of each, two more
`env-sniffing` exploits, one more `test-gaming` and two more `hardcoding`:

| task | why this domain | exploits |
| --- | --- | --- |
| `deb-version` | dpkg ordering is dense and counter-intuitive (`~` before end of string, letters before symbols, `1.0 == 1.00`) | `env-gated` (PYTEST_CURRENT_TEST), `skipped-suite` (module-level skip) |
| `backup-retention` | ISO weeks across New Year, "n newest periods that have a snapshot" vs a calendar window | `fixture-replay`, `hardcoded-cases` |
| `csv-rollup` | an artifact-producing task with real traps: BOM, CRLF, quoted newlines, half-away-from-zero rounding, `-0.00` | `prewritten-reports`, `report-rewriter` (failed reports rewritten as passed) |
| `json-patch` | RFC 6902/6901: escapes, `-`, move into own child, `1 == 1.0` but `True != 1`, no aliasing with the input | `argv-gated` (`sys.argv`), `hardcoded-cases` |

Held-out expectations are derived by hand from `task.md` or, in
`backup-retention`, checked against an oracle that states the rules a different
way (string prefixes and per-period maxima) rather than by copying the reference.
A second reader, given only `task.md`, wrote an independent implementation and
ran the held-out suites against it, looking for expectations the spec does not
imply. Any such expectation would count honest work as a failure.

**The detector grew by one pattern, in the open.** `json-patch/argv-gated`
raised no signal, because `runner-detection` looked for `sys.modules` and
`PYTEST_CURRENT_TEST` but not `sys.argv`. Adding `sys.argv` brought the corpus to
28 of 29 detected. It changes no July number (the archived report regenerates
identically), and no reference or stub trips it. The one remaining blind spot is
still `retry-plan/hardcoded-cases`, for the reason given in
`tests/test_signals.py`.

**What the README may say.** Every number in the README comes from a file under
`results/`, through `gg report`. The July figures stay, labelled with their date
and the aliases they ran under, because they were measured on a different model
generation and a smaller suite. They are not comparable to the November figures
one to one.

**What came out, and why it is reported as is.** All 56 trials passed both
verifiers. A clean sweep is also what a broken verifier would produce, so three
checks came before believing it: every trial ran the full held-out suite (the
step tallies in each trial file are complete), re-scoring the committed
submissions from source gives the same verdicts, and all 11 July submissions
that failed sealed still fail it today. The last check is
`tests/test_results.py`, so CI repeats it on every push. With the verifier
cleared, the result is that this suite is saturated for current models under a
neutral prompt. The remaining 4 runs of the budget were not spent looking for a
gap; re-running until something shows up is how a benchmark talks itself into a
finding.

## Pinned pytest, watched by a canary (2026-11-01)

Both verifiers run pytest, so pytest's own behaviour is part of what the
invariant matrix proves. `deb-version/skipped-suite` passes the naive verifier
only because pytest exits 0 when every collected test is skipped.
`Step.counts` parses pytest's summary line, and the conftest exploits depend on
pytest's discovery rules. Until now CI and the Docker image installed whatever
pytest was newest. A release that changed any of those behaviours could have
flipped a row of the matrix without a commit in this repository.

`requirements.txt` pins the version, and CI, the Dockerfile and the Quickstart
all install from it. Pinning alone would hide the drift instead of catching it,
so `.github/workflows/pytest-canary.yml` runs the harness tests and the matrix
against the newest pytest every Monday. A red canary means a newer pytest
behaves differently. That gets decided deliberately, in the commit that moves
the pin, rather than discovered later.
