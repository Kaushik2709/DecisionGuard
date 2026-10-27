# Developer alpha workflow

Real-user benefit remains unverified; no volunteers are currently enrolled. Requirements and
milestone status remain in the six canonical root documents. These are operating procedures.

## Guided setup and recovery steps

Create a reviewed setup JSON outside captured application source. Use the target environment's
absolute executable. Create any requested linked Git worktrees first:

```json
{
  "coordinator": "reviewer",
  "runner": {"argv": ["D:/YourProject/.venv/Scripts/python.exe", "-m", "pytest", "-q"], "timeout": 120},
  "tasks": [
    {"task_id": "frontend", "actor": "frontend", "worktree": "../YourProject-frontend", "paths": ["frontend", "tests/frontend"]},
    {"task_id": "backend", "actor": "backend", "worktree": "../YourProject-backend", "paths": ["backend", "tests/backend"]},
    {"task_id": "combined", "actor": "combined", "worktree": "../YourProject-combined", "paths": ["frontend", "backend", "tests"], "integration": true}
  ]
}
```

```powershell
decisionguard --root D:/YourProject setup project D:/scratch/setup.json
decisionguard --root D:/YourProject setup project D:/scratch/setup.json --apply
decisionguard --root D:/YourProject doctor
decisionguard --root D:/YourProject next --task-id frontend --task-id backend --integration-task combined
```

Setup previews by default. Apply initializes/registers with deterministic retry keys, preserves
existing runner/coordinator configuration and never accepts contracts or declares assumptions.
Review the runner yourself. For non-Git projects supply global `--state`; isolated integration is
Git-only. If a later task fails, resolve the cause and rerun the same request. Completed tasks
are not duplicated. A changed request has a different identity and may require explicit task/scope
operations. Unknown dependencies are not silently created.

`next` performs a current-source assessment, orders the original findings and saves no receipt.
It changes no declarations, acknowledgement or evidence. Exit 1 means blocked; exit 2 is an
operational/input error. A single-task pass is task readiness, not combined integration. `doctor`
checks integrity, default/task executables and cwd, but does not prove interpreter arguments or
tests are correct. It exits 1 for a diagnosed problem. Run actual configured validation afterward.

Resolve each finding through normal review/lifecycle commands. Refresh updates knowledge; it
does not reconcile code or clear evidence. Never accept a contract solely to silence a warning.
Validate corrected tasks plus the actual separate combined source, then run the ordinary gate
for a persisted point-in-time receipt.

## Disposable reliability checks

```powershell
decisionguard reliability recovery artifacts/recovery-new
decisionguard reliability soak artifacts/soak-new --seconds 30 --workers 2 --history 10000
```

Commands require new disposable destinations and never open the active project's state. Recovery
kills real subprocesses before/after review commit, verifies rollback and replay, observes SQLite
FULL at a page-count ceiling, and restores a backup with invalidated evidence and retained history.
The page ceiling is not a physically full disk.

`reliability filesystem-full <new-dir>` separately requires POSIX and refuses filesystems larger
than 16 MiB. Run only on a dedicated small tmpfs, such as a disposable container's 4 MiB mount.
The retained Linux check fills that mount, not the host disk. Never corrupt or fill real user state
to reproduce a drill; all tests use disposable databases.

Soak uses real linked worktrees, worker processes and a fixed Python assertion. Reports include
validation/gate/snapshot p50/p95, BUSY/errors, concurrent state-change blocks, final quiescent gates,
DB/WAL/SHM sizes and Python tracemalloc peaks. Native SQLite/OS memory is excluded; process RSS is
unknown. History is explicitly seeded fixture events. A worker stops at 100,000 latency samples;
its measured duration exposes early termination. `--seconds 28800` targets eight hours in an
attended/managed session. Short runs never complete that gate. This is not production capacity
or reliability certification. No model requests, cloud resources or providers are used.

## Pilot kit and feedback

```powershell
decisionguard evaluation kit examples/product-study/plan.json artifacts/pilot-new
decisionguard evaluation plan artifacts/pilot-new/plan.json
decisionguard evaluation report artifacts/pilot-new/plan.json artifacts/pilot-new/observations.json
```

The kit copies hashed labels into portable paths and writes empty observations, the exact schema
and participant instructions. It collects no responses and sends no invitations. The included
plan remains a planted fixture. Replace cases, participant aliases, source fingerprints, baseline
configurations, dates and criteria with an independently reviewed real plan before a pilot;
re-inspect and retain the resulting digest before executing tasks.

Pilot feedback requires actual response evidence and `consent_to_use: true`. Record voluntary
continuation plus pricing interest: `not_asked`, `would_consider`, `would_not_pay`, `unknown`.
Optional volunteered `monthly_budget_minor` and three-letter `currency` must appear together.
These are stated preferences, not purchases, revenue or proof of paid demand. Collect no payment
details or identifiable contacts through this format. Missing replies remain missing. See
[PRODUCT_EVALUATION.md](PRODUCT_EVALUATION.md) for matched-task design and metric limitations.

## Release checks

CI installs pinned Node fixture tools and requires the strong baseline test, runs the locked
suite/lint/types/build, and retains JUnit/distribution reports plus build artifacts for seven days.
It does not publish. Remote evidence requires an actual run against reviewed source in GitHub.

```powershell
uv build
uv run python scripts/verify_distribution.py dist/decisionguard-0.1.0-py3-none-any.whl --output artifacts/distribution-new.json
```

Distribution inspection checks required modules, packaged skill, typing marker, exact license and
metadata, excludes local state, and records wheel/file hashes. Test the installed wheel from a
separate working directory with supported dependencies, CLI and a real MCP client. Preserve the
reports. Neither artifact checks nor dependency metadata inventory approve security or stable
release. Full-duration soak, real usage/adoption, optional classifier evaluation, remote CI,
private reporting configuration and third-party license/provenance review remain separate gates.
