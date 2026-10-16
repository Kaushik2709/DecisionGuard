# Implementation tasks

- [x] M0: canonical specifications, entry points, package/lockfile, official API verification, CI.
- [x] M1: models, compatibility, migrations, shared state, events, idempotency, authority, concurrency.
- [x] M2: CLI and executable checkout vertical slice; clean merge mismatch, blocked ack, repaired pass,
  rejection and explicit conversion path.
- [x] M3: official stdio MCP tools and real client transport tests; setup instructions.
- [x] M4: source/config/decision freshness, isolated combined gate, portable metadata, CI example.
- [x] M5: thin documented harness skill, labeled benchmark, README, limitations, release verification.

## Acceptance commands
`uv sync --locked --group dev`; `uv run ruff format --check .`; `uv run ruff check .`;
`uv run mypy`; `uv run pytest`; `uv run decisionguard demo`; `uv run decisionguard benchmark`.
The transport suite must launch a real SDK stdio client. Demo and benchmark must use no API keys.
Optional AI extraction (M6) is deferred.

## Production-readiness and objective review — 2026-10-16

Assessment compares live source with the original attached brief and the approved deterministic
M0–M5 scope. The core is implemented; production reliability and interactive agent effectiveness
still require the gates below. MIT licensing is distribution permission, not security certification.

| Original objective | Current assessment |
|---|---|
| Shared contracts and decision versions across worktrees | Implemented with common-directory SQLite, immutable versions and atomic reviews |
| Separate delivery, acknowledgement, refresh and tested implementation | Implemented; acknowledgement alone cannot clear the gate |
| Reliable revalidation against current decisions and source | Implemented with latest-run sequence, generation, configuration and source bindings |
| Validate actual combined implementation | Implemented for distinct integration task/worktree and approved declared scope |
| Early targeted change warnings | Works for declared dependents; verified path-only notification gap remains |
| Compatible conversion adapters | Reviewed metadata and real conversion tests exist; cross-boundary mappings do not themselves prove adapter semantics |
| CLI/MCP and harness-independent core without API keys | Implemented; interactive skill adoption/compliance remains unverified |
| Meaningful evaluations | 79-test matrix and planted demo/benchmark exist; no live-agent effectiveness or production reliability estimate |

### P0 — before a stable production claim

- [ ] Align impact notifications with gate relevance. Reproduction in
  `artifacts/production-review-0e9aaa2b`: an observer task with overlapping `check.py` scope but
  no declared contract dependency gets a `pending_impact` finding yet zero poll events, and is
  absent from `affected_tasks`. Notify the union of declared dependents and relevant path tasks;
  accepted scope changes must account for old and new scope. Preserve acknowledgement semantics.
- [ ] Exercise reviewed/adapter benchmark scenarios through actual services, gates and runner
  evidence. Current `evaluate()` forces `clear` for independent/adapter/reviewed relationship
  labels; these rows alone do not measure the corresponding service behavior. Keep simulations
  labeled and include missing/broken adapter and review cases with suitable expected outcomes.
- [ ] Make runner interruption/descendant cleanup explicit and tested. Verify Ctrl+C, timeout,
  parent exit with live descendants and inherited output pipes on Windows/Linux. This is
  process lifecycle control; the approved local tool still trusts same-user code.
- [ ] Configure the real repository, run remote CI with required checks and retain its evidence.
  This workspace currently has no root Git repository or remote. Review the push scope first.
- [ ] Pilot the actual Codex workflow with 2–4 agents on representative real repositories;
  exercise missed polling, restarts, competing changes and scope approval. Record warnings,
  combined correctness, rework, elapsed time and tool overhead; set acceptance criteria before
  presenting effectiveness claims. Compare matched baseline tasks if claiming improvement.
- [ ] Test wheel installation outside the source checkout with supported Python/OS versions,
  CLI and real MCP smoke tests, and v1 migration using retained release fixtures. Define supported
  versions, stable API/schema changes and a release/version/changelog policy.

### P1 — operational maturity

- [ ] Exercise actual process crashes, disk-full/read-only/busy/corrupt state, interrupted setup,
  migration and backup restoration; publish tested diagnosis/recovery procedures. Existing
  fault-injection and restore regressions are useful initial evidence.
- [ ] Run repeated concurrency/soak and large-history tests; measure gate/snapshot p50/p95 latency,
  peak memory, WAL/disk growth and lock contention. Bound queries over historical JSON entities
  and add targeted indexes as measured needs justify them.
- [ ] Define task archival and event/run-output/idempotency retention without breaking replay or
  restoring stale authority. Existing maintenance prunes receipts only; other history grows.
- [ ] Add a verified private vulnerability-reporting channel, supported-version policy, honest
  maintainer response expectations, dependency-update process and secret-safe diagnostic policy.
- [ ] Review dependency licenses and provenance, retain required third-party notices, and provide
  a release dependency inventory/SBOM. The project MIT license does not relicense dependencies.
- [ ] Establish a tagged release pipeline with controlled publication, artifact hashes/provenance
  and installation/upgrade documentation. Do not publish until the owner/repository is configured.

### MIT licensing delivered

- [x] Add standard MIT `LICENSE`, using `Copyright (c) 2026 Kaushik Mukherjee`.
- [x] Declare `license = "MIT"` and `license-files = ["LICENSE"]`; require Hatchling >=1.27
  for PEP 639 metadata. README links the license and explains dependency-license boundaries.
- [x] Build source archive/wheel offline and verify the exact license text is included in both,
  with `License-Expression: MIT` and `License-File: LICENSE` in wheel metadata; lock check passes.

The copyright holder is Kaushik Mukherjee, as explicitly supplied by the user.
No repository or package was published. Local SQLite,
manual checkpoints and the deterministic core remain appropriate for the original local-tool
objective. Multi-user hosting or isolation of hostile agents would require a separate scope.

## Security audit follow-up (2026-10-15)

The implementation milestone checks above do not mean production security clearance.
See `docs/SECURITY_AUDIT.md` for seven reproduced adverse behaviors and their threat models.

- [x] DG-01: reject changed files outside approved task scope before integration clearance.
- [x] DG-05: prevent historical successes from overriding newer failed validation.
- [x] DG-02: enforce distinct implementation/integration tasks and worktrees.
- [x] DG-03: bind evidence to a task invalidation generation.
- [x] DG-04: provide effective coordinator revocation for existing sessions.
- [x] DG-06: constrain out-of-scope pending proposals and add resource budgets.
- [x] DG-07: make interrupted initialization safely recoverable.
- [x] Replace audit reproduction assertions with fail-closed regression expectations.
- [x] Add database v2 backup/migration, retention command and recovery/rollback tests.
- [x] Pin CI actions and add dependency auditing; correct self-integration instructions.
- [x] Bound path enumeration before allocation; terminate stalled/oversized Git producers,
  prune excluded non-Git trees, and apply the same budgets to changed-path scans.
- [ ] Execute remote GitHub Actions after the project has a configured repository.
- [ ] Trial interactive multi-agent skill compliance on a real project.

## Completion verification — 2026-10-16

The approved deterministic implementation and seven audit remediations are complete for
the trusted local-tool scope. The two unchecked external validations above remain explicit.

| Final environment / check | Executed result |
|---|---|
| Windows Python 3.11, workspace-local environment | 79 passed in 259.66s |
| Windows Python 3.12, project environment | 79 passed in 261.59s |
| Linux Python 3.11, isolated offline Docker execution | 79 passed in 27.38s |
| Linux Python 3.12, isolated offline Docker execution | 79 passed in 27.95s |
| Ruff | Check passed; 52 files formatted |
| mypy | Passed, 25 source files; Windows and Linux |
| Demo / benchmark | Demo passed; 14/14 classifications and 7/7 lifecycle checks on Windows 3.12 and both Linux versions |
| Distribution | Source archive and wheel built offline on Windows and both Linux versions; final Windows wheel contains bounded enumeration |
| Dependencies | Refreshed OSV audit: no known vulnerabilities/adverse statuses in 48 packages |
| Workflow | Offline actionlint passed |

Windows JUnit results: `artifacts/completion-windows311-20261016.xml` and
`artifacts/completion-windows312-20261016.xml`. The new enumeration suite additionally verifies
count/name-byte limits, excluded/state directory pruning, empty-directory traversal limits,
deadline enforcement on empty source, and termination of stalled Git producers. Receipt
pruning emits success after commit. Configuration now defaults `snapshot_name_bytes` to
16 MiB, which changes evidence configuration digests and requires fresh validation.
Initial container entrypoints attempted an expired package-index refresh with networking
disabled; final runs used their preinstalled environments directly and all checks passed.
No user database, global harness configuration, remote repository, or deployment was changed.

## Hardening verification — 2026-10-15

| Environment / check | Executed result |
|---|---|
| Windows Python 3.11.15, isolated workspace environment | 73 tests passed in 217.27s |
| Windows Python 3.12.8 | 72 tests passed in 181.88s; subsequently added serialization test passed separately |
| Linux Python 3.11.17, disposable Docker container | 73 tests passed in 28.94s; Ruff and mypy passed |
| Linux Python 3.12, disposable Docker container | 73 tests passed in 25.14s; Ruff and mypy passed |
| Demo and benchmark | Repaired demo passes; benchmark 14/14 classifications and 7/7 lifecycle checks on Windows 3.12 and Linux 3.11/3.12 |
| Packages | Source archive and wheel built on Windows and both Linux versions |
| Dependencies | `uv audit --frozen`: no known vulnerabilities/adverse statuses in 48 packages |
| CI workflow | Pinned official action commits; local actionlint passed |

Windows JUnit reports are in ignored `artifacts/hardening-windows-final.xml` and
`artifacts/hardening-windows311.xml`. Linux tests ran with network disabled and read-only
source/test mounts. Python 3.11 installation, dependency caches, and test environments stay
inside the workspace; disposable images are tagged `decisionguard-hardening:3.11` and `:3.12`.
No actual project state was migrated. Migration backup/restore, rollback, initialization fault
boundaries, latest-run ordering, source scope, quotas, writer-lock availability, and live MCP
revocation are covered by regressions. Historical probe assertions have been reversed.

Verification exposed and corrected cross-platform type checking, unpicklable GuardError,
and demo/benchmark assumptions about broad proposal scope and self-integration. An initial
Linux 3.11 multiprocessing failure was masked by exception serialization; its isolated rerun
and the subsequent full suite passed. Remote GitHub Actions and interactive multi-agent
harness compliance remain unverified; local Docker checks do not claim those results.
