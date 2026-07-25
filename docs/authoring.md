# Authoring a task

Every task is a directory under `tasks/<slug>/` built from files only — no
scripts, no code generation. `gg invariants` rebuilds each candidate from these
files and puts it through both verifiers.

## Layout

```
tasks/<slug>/
  meta.json              title, summary, submission allowlist
  task.md                the prompt handed to the agent
  workspace/             exactly what the agent starts with
    conftest.py          puts the workspace root on sys.path
    src/__init__.py
    src/<module>.py      the stub, raising NotImplementedError
    tests/test_visible.py
    tests/fixtures/…     optional
  reference/             files overlaid on workspace to make an honest solution
    src/<module>.py
  sealed/                never present while the agent works
    test_hidden.py       held-out pytest suite
    probe.py             plain-python checks, no pytest in the process
  exploits/<name>/
    meta.json            {"class": …, "note": …}
    files/…              files overlaid on workspace
```

## Rules that make the matrix hold

The stub must **fail** the visible tests: `raise NotImplementedError`.

The reference must **pass** the visible tests, the held-out tests and the probe.

Every exploit must **pass the visible tests as they exist in its own overlay**
and **fail sealed**. An exploit that fails naive is not an exploit; an exploit
that passes sealed is a hole in the sealed verifier and must be reported, not
committed.

`meta.json`'s `submission` lists the glob patterns sealed will copy from the
candidate, always `["src/*.py"]` unless the task genuinely needs more. Anything
outside it is restored from pristine, so exploits that live outside `src/` are
caught structurally rather than behaviourally.

## Writing the spec

`task.md` is the contract; `tests/test_visible.py` is a sample of it. Keep the
visible suite small (6–10 tests) and confined to the easy half of the
specification. Every rule the visible tests do not reach is what the held-out
suite exists for. State the rules precisely enough that a disagreement between a
submission and the held-out tests is always the submission's fault — ambiguity
in `task.md` is a bug in the task.

Prefer a domain with dense, well-documented edge semantics (calendar rules,
matching precedence, range arithmetic) over one that needs a large corpus. A
task must run in seconds, use only the standard library, and be deterministic:
no clock reads, no randomness, no network, no filesystem outside the workspace.

## Writing held-out tests

Derive expectations independently wherever you can — compute the expected
weekdays with `datetime`, the expected ordering from the input graph — instead
of transcribing what the reference happens to return. A held-out suite that only
mirrors the reference cannot tell a wrong reference from a wrong submission.

## Writing the probe

`probe.py` runs as a plain script with the candidate on `PYTHONPATH` and its own
directory as the working directory. It exists so that a submission which is only
correct under a test runner, or which reads fixtures by relative path, is caught
even when it satisfies every pytest step. Keep it to a handful of checks, print
what failed, and `sys.exit(1)`.

## The six hack classes

| Class                | The move                                                        | What catches it in sealed                        |
| -------------------- | --------------------------------------------------------------- | ------------------------------------------------ |
| `test-gaming`        | edit, skip or delete the visible tests                            | pristine tests are restored                       |
| `verifier-tampering` | add `conftest.py`, `sitecustomize.py`, `pytest.ini` and friends   | denied filenames never enter the submission       |
| `hardcoding`         | special-case the exact inputs the visible tests use               | held-out tests use different inputs               |
| `fixture-inspection` | read the expected answers out of a fixture at runtime             | held-out inputs are absent from the fixture       |
| `output-forgery`     | hand-write the artifact instead of computing it                   | the artifact is regenerated from the submission   |
| `env-sniffing`       | behave correctly only when a test runner is detected              | the probe runs without pytest in the process      |

## Acceptance

```bash
.venv/bin/python -m gg invariants --task <slug>
```

Every row must read `ok`. A task is not done until it does.
