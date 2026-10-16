# Project checkpoint

## Copyright holder finalized — 2026-10-16

User explicitly supplied `Kaushik Mukherjee` for the MIT copyright holder. LICENSE, README
and the licensing checklist now use `Copyright (c) 2026 Kaushik Mukherjee`; the prior collective
notice below is historical. Offline build passed; exact updated LICENSE contents verified in
both the source archive and wheel. No runtime code changed or package was published.

## Production-readiness / licensing review — 2026-10-16

User asked what remains for production, MIT licensing, and alignment with the original goal.
Read original pasted brief, current canonical docs, source and package metadata. Core deterministic
M0–M5 aligns; production and interactive real-agent effectiveness remain unproven. Confirmed an
additional workflow gap with a disposable real service/Git fixture: overlapping path-only task
gets `pending_impact` in conflicts but no durable poll notice or `affected_tasks` membership.
Reproduction retained at `artifacts/production-review-0e9aaa2b`. This is recorded as P0 alongside
service-backed benchmark scenarios (some rows currently force clear by relationship label),
runner cancellation/descendant cleanup, remote CI, real agent pilots and installed-wheel tests.
P1 covers operational fault/soak testing, history retention, release/reporting policies and
third-party license inventory. Full objective matrix and ordered backlog are in tasks.md.

MIT license added to root LICENSE, README and pyproject PEP 639 metadata. Copyright notice
uses `2026 DecisionGuard contributors` as the stated collective default; asynchronous question
requested preferred holder name. No personal name/email was invented. Hatchling minimum is
now 1.27 per official PyPA documentation; cached backend is 1.32.4. `uv lock --offline`, lock
check and offline build passed; exact LICENSE present in wheel/source archive, wheel metadata
has License-Expression MIT and License-File LICENSE. Runtime source unchanged in this review;
no full suite rerun for metadata/docs-only edits. Prior 79-test matrix remains the latest runtime
evidence. No remote publication, deployment, user-state migration or personal-memory edit.

## Completion checkpoint — 2026-10-16

User requested finishing the approved implementation. Canonical requirements and live source
were inspected. All seven audit remediations remain implemented; final review additionally
fixed enumeration that materialized names before checking resource budgets. Git now streams
NUL-delimited names with count, byte and deadline enforcement and kills stalled producers.
Non-Git traversal is incremental, prunes state/exclusions and bounds directory traversal;
changed-path scans share configured budgets. New optional `snapshot_name_bytes` defaults
to 16 MiB. Its addition changes configuration digests: existing v2 installations need fresh
validation too. Pruning now reports success only after commit. Six new regressions added.

Final full suite: 79 passed on Windows 3.11 (259.66s), Windows 3.12 (261.59s), Linux 3.11
(27.38s), Linux 3.12 (27.95s). Ruff passes (52 formatted files); mypy passes for 25 source
files on both platforms. Windows/Linux demo and planted benchmark pass (14/14, 7/7).
Offline builds pass, final Windows wheel inspected for the new enumerator and name budget.
Online `uv audit --frozen` reports no known vulnerabilities/adverse statuses in 48 packages.
Actionlint passes. JUnit reports and exact results are linked in tasks.md.

Docker images are reused with source/tests mounted read-only and networking disabled. Their
default `uv run` entrypoints tried to refresh expired build metadata; use installed binaries
directly (`.venv/bin/python -m pytest`, `.venv/bin/python -m mypy`, etc.) or explicit offline
mode. These were environment-only failures before the test runs; final checks passed.
Remote CI cannot run from this non-Git workspace without a configured repository. Interactive
multi-agent harness/skill compliance remains a separate external trial. No user state was
migrated, no global configuration changed, and no commits/publishing/deployment performed.
Implementation is complete within the approved trusted same-user model. Older notes below
are historical; tasks.md contains the latest verification and remaining external checks.

## Security hardening implementation — 2026-10-15

Approved local-tool hardening implemented. Seven original probes now assert rejection/recovery.
Database v2 adds scope approval/revision, evidence generation, run sequence/latest pointer and
entity mutation epoch. Explicit `migrate --sessions-stopped` backs up v1 state, preserves history,
invalidates runs and requires scope reapproval. New CLI: `approve-task-scope`, `prune-receipts`.
MCP registration awaits scope approval; trusted CLI registration approves supplied scope.
Proposal/task quotas and chunked snapshot limits use optional config `limits` defaults.
Gate uses latest evidence, rejects out-of-scope changes and self/same-worktree integration,
captures outside writer transactions and rechecks epoch before receipt commit.
Authority is reloaded on mutation/retry; real stdio revocation test added. Setup journals its
identity, locks administrative work and atomically publishes config. Scope changes invalidate
evidence. Demo/benchmark use an explicitly approved broad proposal task; alternate adapter
candidate uses a single-task gate, not self-integration. Platform-dependent typing and
GuardError multiprocessing serialization were corrected during Linux testing.
CI actions pinned to official tags resolved via `git ls-remote`; advisory audit added.
No actual user project database was migrated. Disposable Docker images and workspace-local
Python 3.11 environment were created for verification; global harness settings remain untouched.
Final verification is recorded in tasks.md. Remote CI and interactive live-agent compliance
remain unverified. Historical audit notes below describe the pre-hardening state.

## Adversarial audit — 2026-10-15

User requested a security/AI-engineering breakdown and attempts to break the project.
Audit delivered in `docs/SECURITY_AUDIT.md`; production source remains unchanged.
Seven adverse behaviors reproduced by `tests/security_audit/test_adversarial_audit.py`:
omitted changed code in combined source (high), historical passing run overriding a newer
failure (high), reused integration task/worktree, in-flight refresh invalidation race,
startup-only coordinator revocation, broad pending-proposal blockage, and initialization
failure recovery. Last five are medium-priority findings with qualifications in the report.
Audit assertions currently confirm unsafe behavior; passing them is not security clearance.
Existing 38 tests plus initial six probes passed (44 in 99.90s); final seven probes passed
(18.21s). Ruff check/format and mypy passed. Approved online `uv audit --frozen` reported
no known vulnerabilities/adverse statuses in 48 packages. Initial sandbox network attempt
failed; successful retry queried OSV. SQLite runtime is 3.45.3, not certified by that scan.
Remediation checklist added to tasks.md. No repairs, remote CI, live-agent security trial,
destructive stress tests, or global configuration edits were performed.

## State — 2026-10-15

Deterministic v1 M0–M5 is implemented. Workspace began empty; work was sequential.
Canonical docs are PRD, architecture, design, rules, tasks, and this checkpoint.
Optional AI extraction (M6) remains deferred. No global harness configuration was modified.

## Implemented

- Immutable decisions/tombstones, explicit review, typed assumptions, dependency refresh,
  reviewed compatibility mappings, durable delivery/ack cursors, and resolution history.
- Shared Git-common-directory SQLite with WAL, bounded busy wait, migration version checks,
  optimistic predecessor checks, atomic invalidation/events, and payload-bound retry records.
- CLI and fixed-actor official SDK v1 stdio adapter sharing services; structured domain errors.
- Configured local runner with timeout/output bounds, source/config/revision bindings,
  interrupted-run behavior, isolated combined-source gate, and reviewed metadata portability.
- Disposable real Git checkout demo, fixture evaluation, portable workflow skill, and CI examples.

## Verification on Windows / Python 3.12.8

Commands used the project `.venv` directly after uv setup. All results below were executed:

| Command | Result |
|---|---|
| `uv sync --locked --group dev` (workspace-local cache) | Passed; 49 locked packages, MCP 1.30.0, Pydantic 2.14.1, Typer 0.27.3 |
| `.venv/Scripts/ruff.exe format --check .` | Passed; 44 files already formatted |
| `.venv/Scripts/ruff.exe check .` | Passed |
| `.venv/Scripts/mypy.exe` | Passed, 24 source files |
| `.venv/Scripts/python.exe -m pytest -q --basetemp artifacts/pytest-complete` | 38 passed in 82.79 seconds |
| `.venv/Scripts/python.exe -m decisionguard.adapters.cli demo` | Passed all required lifecycle and adapter paths |
| `.venv/Scripts/python.exe -m decisionguard.adapters.cli benchmark` | 14/14 classifications, 7/7 lifecycle checks; 19.8713 seconds |
| `python <bundled skill-creator>/scripts/quick_validate.py skills/decisionguard-workflow` | Skill valid |
| `uv build --offline` | Built source archive and wheel in `dist/` |

The suite includes real process contention and real SDK stdio initialization/tool calls;
the demo's combined test actually fails with `499 != 49900` before repair. Benchmark precision
is 6/6 and recall 6/6, with zero false positives/negatives and two unknown classifications.
These are planted diagnostic fixtures and deterministic simulated agents, not production or
live-LLM evaluations. Reports are retained under ignored `artifacts/`.

## Corrections made during verification

Ruff initially scanned the dependency cache in the empty, non-Git workspace. Explicit cache/
artifact exclusions were added and all dependencies reinstalled from a fresh cache before
verification. Network-restricted wheel building succeeded offline from that clean cache.
Git subprocesses now use DEVNULL stdin: inherited MCP stdin caused a real context-call stall.
The transport test retains bounded request timeouts. Concurrent review tests use a filesystem
rendezvous and real spawned processes rather than a network-backed multiprocessing manager.
Final review added committed-change coverage relative to task registration, validated portable
history with atomic rejection of malformed imports, rejection of stale losing proposals, and
CLI exit code 2 for runner operational errors. Regression checks cover these cases.

## Remaining limits and next steps

Windows local evidence is verified; configured Windows/Linux CI has not run remotely.
No interactive Codex session compliance or installed-skill discovery was tested; skill delivery,
official configuration instructions, and real MCP transport were verified separately.
Coverage is declared. Snapshots exclude Gitignored untracked files/reviewed generated paths;
pre/post content hashes cannot detect malicious edit-and-restore or environment-only changes.
Any project revision change conservatively requires fresh evidence. SQLite/local configuration
trusts the same user. Gates cannot make future merges atomic. No commits or remote publishing
were performed. Next practical step: run configured CI and trial the workflow on a real project.
