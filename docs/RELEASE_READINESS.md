# Current release readiness

Status: local alpha. This checklist owns current release gates; older dated reviews
in tasks.md and memory.md are historical evidence. Passing one gate cannot complete
another. Main is 0.1.0/schema 3; automation 0.2.0a1/schema 4 remains in its separate
implementation worktree and requires its own reviewed integration and host trials.

## Implemented hardening - 2026-10-30

- Require certifi >=2026.10.18 in package metadata; lock to 2026.10.23.
- Refuse affected SQLite runtimes before state access; report actual runtime safety
  through `runtime` and `doctor`. Provide hash-verified private runtime preparation.
- Run dependency auditing as a separate required CI job. Matrix failures no longer
  cancel other platforms; an audit failure still fails the workflow.
- Require runtime preflight and installed-wheel transport/lifecycle/concurrency checks
  from a separate environment/cwd. Preserve JUnit and runtime provenance artifacts.
- Report native worker peak RSS and sampled database/WAL/SHM peaks in soak results.
- Keep the weak-check negative control and demonstrate that a concrete behavioral
  assertion blocks the same undeclared unit bug until implementation repair.

## Release gates

- [ ] Exact release revision passes the independent audit job and all four
  Windows/Linux, Python 3.11/3.12 verification jobs, including installed-wheel checks.
  Local changes do not change the already-failed historical remote run.
- [ ] Each supported runtime passes the actual SQLite preflight. Windows x64 is
  verified locally; remote Linux results and any extra supported combinations need
  their own evidence. No macOS/ARM support claim is made by this matrix.
- [ ] Retain the complete eight-hour two-to-four-worker run, latency distributions,
  native worker memory, sampled state-file peaks, lock/error counts and recovery evidence.
- [ ] Broader real-agent pilots cover missed polls/events, restart, competing proposals,
  explicit review, scope approval and current combined-source validation. The existing
  controlled two-session workflow does not establish general effectiveness.
- [ ] Verify an owner-controlled private reporting channel and review dependency
  licenses/provenance. Inventory metadata alone is not a completed license review.
- [ ] Review/tag the release, retain hashes and installation/rollback evidence, and
  obtain publication approval. A CI workflow pass does not publish or approve a release.

## Reproduce checks

First follow [runtime setup](RUNTIME_SETUP.md). Then:

```powershell
uv audit --frozen
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --basetemp artifacts/pytest-release --junitxml artifacts/release-tests.xml
uv build
uv run python scripts/verify_distribution.py dist/decisionguard-0.1.0-py3-none-any.whl --output artifacts/distribution-release.json
uv run python scripts/verify_installed.py dist/decisionguard-0.1.0-py3-none-any.whl --output-dir artifacts/wheel-release
uv run python scripts/run_soak.py artifacts/soak-release-new --report artifacts/soak-release-new.json
```

Use new artifact paths when rerunning checks. `run_soak.py` defaults to eight hours
and atomically records running/completed/failed status, source hashes and actual
results. An interrupted/still-running record is not a completed reliability gate.
Peak RSS is the maximum lifetime peak of one worker and excludes parent/runner
children; sampled state-file maxima are not continuous disk telemetry.

Configured tests should assert concrete consumer/provider outcomes: money/time units,
unauthorized-call rejection, bounded retry attempts, repeated-idempotency-key effects,
optional-field semantics and actual combined HTTP behavior. Preserve unknown coverage;
do not replace missing assertions with declared compatibility. See the strong baseline
fixture and `tests/integration/test_semantic_case_boundaries.py`.
