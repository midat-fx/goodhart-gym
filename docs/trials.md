# Reading a trial file

Each agent run leaves one file, `results/<run>/<model>/<task>-t<N>.json`. It
holds everything the published numbers are computed from, so a reader can check
any row of `docs/results.md` without re-running an agent.

`gg rescore results/<run>` checks the claim mechanically. For every trial it
builds a pristine workspace from the task, writes the stored `submission` over
it, runs the sealed verifier again and compares the result with `sealed_pass`.
It prints each mismatch and exits non-zero on any. CI rescores only the 11 July
sealed failures, through `tests/test_results.py`. A full rescore of both runs
takes about a minute.

## Top level

| field | meaning |
| --- | --- |
| `task` | task slug, a directory under `tasks/` |
| `model` | the value passed to `--model`. November used explicit ids; July used the `haiku` and `sonnet` aliases |
| `trial` | 1-based trial number for this task and model |
| `naive_pass` | the agent's own workspace passed `python -m pytest tests`, run where the agent left it |
| `sealed_pass` | the sealed verifier passed: pristine visible tests, held-out tests and the probe, run on the accepted submission only |
| `gap` | `naive_pass` and not `sealed_pass`. A gap is a disagreement between the verifiers, not proof of cheating |
| `hack_signals` | the signals the detector raised when the trial ran. Kept for the record only: `gg report` recomputes them from `submission`, so a better detector moves the published counts without new runs |
| `caught_by` | for a gap trial, the first sealed step that failed, or `submission allowlist` when the visible tests failed after files had been dropped. Empty otherwise |
| `dropped` | files the agent created or changed outside the task's submission allowlist, each with its reason: `(not in submission allowlist)` or `(modified, restored from pristine)` |
| `changed_files` | every file that differs from the stub workspace, cache directories excluded |
| `submission` | path → source text of `src/**/*.py` as the agent left it. Every task's allowlist is `src/*.py`, so this covers everything the sealed verifier accepted. Rescoring and signal detection read it |
| `sealed_steps` | one entry per sealed step: `name`, `passed`, `passed_count`, `total_count` |
| `command` | the agent CLI's argv, with the prompt replaced by `<prompt>` |

The counts in `sealed_steps` come from pytest's closing summary line. The probe
is plain Python, not pytest, so its counts are always 0 of 0, and only `passed`
says how it went.

## Inside `agent`

| field | meaning |
| --- | --- |
| `timed_out` | the run hit the harness timeout (900 s by default) and was killed |
| `wall_seconds` | wall time of the CLI process |
| `num_turns` | turns reported by the CLI; null when it reported nothing |
| `cost_usd` | the API-equivalent cost the CLI reported, not what was billed |
| `is_error` | the CLI's own error flag |
| `stop_reason` | why the model's last turn ended, as the CLI reported it |
| `parse_error` | the tail of the CLI output when it was not JSON. Absent from both committed runs: the field was added after them |
| `models_used` | the model ids the API actually served, taken from the CLI's `modelUsage` |
| `cli_version` | output of `claude --version` |

July trials have no `models_used`, `cli_version` or `parse_error`, so which
models served those aliases is unrecorded. The report says so instead of
guessing.

Runs that never reached the model (an error at zero cost, or no parsable
result, with no file changed) leave no trial file at all. The next `gg run`
into the same directory retries them, because it skips only trials that have a
file.
