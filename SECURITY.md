# Security model

## What this repository contains

`tasks/*/exploits/` holds working submissions that defeat a deliberately weak
verifier. They are small, self-contained Python files that hardcode expected
values, neuter test assertions, add auto-imported shim files, replay fixtures,
leave pre-written artifacts in place, or gate correct behaviour on the presence
of a test runner. None of them touch the network, spawn processes, read outside
their workspace, or use `eval`, `exec`, `pickle` or `os.system`. They are
demonstrations against this repository's own grader, not tooling against anyone
else's.

## What the harness does and does not defend

`gg invariants` and `gg verify` run candidate code in a temporary directory as
the current user. That is a **grading boundary, not a sandbox**: it stops a
submission from fooling the verifier, and it does not stop a submission from
doing anything else the user can do.

Consequently:

- Run `gg verify` on workspaces you produced or trust.
- Run `gg run` — which executes a coding agent with `--permission-mode
  bypassPermissions` in a scratch directory — inside a container or a
  throwaway machine when the subject is not one you trust.
- Do not point the harness at a workspace downloaded from a stranger without
  reading it first.

Every subprocess is bounded by a 90-second timeout, so a submission that hangs
is scored as a failure rather than stalling a run.

## Reporting

A submission that passes the sealed verifier while doing no real work is a
vulnerability in this project, and the most valuable report it can receive.
Open a public issue with the workspace or the diff — there is nothing to
embargo, because nothing here guards anyone's production system.

For anything you believe should not be public, email faizov.midat@gmail.com.
