# Implementation tasks

## Same-repository Codex MCP test preparation - 2026-10-27

- [x] Initialize this repository's shared state and prepare snapshot-based linked coding/
  integration worktrees without changing main HEAD/index or committing user work on main.
- [x] Verify separate Codex actor/root configurations and real producer MCP proposal ->
  consumer pending_impact delivery. Current chat can read this project's MCP context.
- [x] Verify worktree-local transport runner: 4 passed; retain prompts, operator requests,
  exact state and limitations in artifacts/codex-repo-test-20261027/RUNBOOK.md and memory.md.
- [x] Explicit owner baseline review: approved 2026-10-27, accepted version/revision 1;
  native MCP context and queued accepted events 4/5/6 verified without advancing delivery.
- [x] Controlled two-Codex-session proposal/discovery: producer proposed retryable field;
  consumer polled matching pending_impact event 9; both have passing four-test runner evidence
  yet fresh gates block solely on pending_impact. Actual state/screenshots verified 2026-10-27.
- [x] Verify accepted v2 and actual producer/consumer edits; consumer fresh validation fails
  against old producer as expected. Combine four reviewed files in the integration worktree.
- [x] Correct integration MCP test source selection (SDK env filtering); fresh configured
  combined-source tests 4 passed in 12.09s, plus startup-error smoke and selected lint/format.
- [x] User explicitly approved consumer integration scope; reviewer CLI applied revision 1.
  Synchronized reviewed source with backups/hash checks, freshly validated consumer (4 passed,
  11.99s, one nonfatal cache warning). Producer and integration evidence remained current.
- [x] Full multi-task integration gate passed at revision 2: integration_checked true,
  findings [], receipt cbe798ab-933b-4d06-86f6-21dfb940ade9. Controlled live test complete;
  same four tests across three worktrees, no new full-project matrix or production approval.
  Report: artifacts/codex-repo-test-20261027/completed-live-test-report.md. No main merge/push.

## Different-case verification - 2026-10-21

User requested checking multiple cases beyond the checkout demonstration. Current Windows
Python 3.12 run: benchmark 34/34 expected classifications (16 conflict/12 clear/6 unknown),
7/7 lifecycle checks, and 64 focused integration/regression tests passed (182.32s, no skips).
Benchmark runtime: 97.088s. This selected run is not a new full-project/OS matrix.

Added tests/integration/test_semantic_case_boundaries.py: a reviewed conversion cannot override
an actual failing implementation test; repair plus fresh validation clears it. A separate
negative control deliberately keeps declarations unchanged and uses only a nonempty assertion:
the hidden unit/business mismatch escapes and the gate passes. This confirms the documented
coverage limit, not successful detection. Do not describe all 64 checks as caught application bugs.

Cases include money/time/auth/retry/idempotency/error declarations, schema directionality,
unknown compatibility, pending/rejected/competing reviews, source/config/decision freshness,
retry behavior, combined source, scope/coverage, and the actual TS/Python strong baseline.
Report and raw JSON/JUnit: artifacts/case-validation-20261021/report.md. New tests passed Ruff;
no core implementation, real project state, global settings or main-repository history changed.

## Product alpha improvements - approved 2026-10-20

Work sequentially and preserve the existing working tree. No volunteers are available: pilot
execution, adoption and willingness to pay remain external evidence, not implementable results.

- [x] M12b: preview-first project onboarding with resumable explicit apply, current-source
  next-action guidance, and diagnosis of task-specific runner availability.
- [x] M12c: real killed-writer/retry recovery, bounded storage-exhaustion drills, repeatable
  multiprocess soak and large-history measurement. Short runs must not complete the 8-hour gate.
- [x] M12d: a runnable strong schema/codegen/contract/integration baseline fixture, pilot kit with
  consented feedback and pricing-interest recording, and retained local release checks/CI reports.
- [ ] External gates: volunteer trials, real adoption/payment evidence, remote CI on these changes,
  full-duration soak and owner-configured publication/private reporting. No automatic publication.

Acceptance: onboarding/next do not accept decisions, hide findings, execute preview commands or
clear gates. Retry cannot duplicate completed setup. Recovery preserves accepted history and
never restores passing stale evidence. Performance reports include workload, elapsed duration,
errors, p50/p95 and state growth; fixture results remain fixture-only. Record actual checks and
limitations below and in memory.md after each milestone.

M12b focused Windows verification: 9 passed (13.50s initial run); final retained rerun is
artifacts/onboarding-windows.xml. Ruff passed and strict mypy passed for 39 modules. Setup and
next are local CLI workflows; no real project was initialized by these disposable tests.

M12c: Windows recovery/drill tests 7 passed, 1 bounded-filesystem skip (10.69s), report
artifacts/reliability-windows.xml. Actual Linux storage exhaustion ran separately on a new 4 MiB
Docker tmpfs: 1 passed (0.21s), artifacts/filesystem-full-linux312.xml. No host disk was filled.
The `reliability recovery` CLI also passed on its own disposable repository. Windows two-worker
30-second workload with 10,000 seeded historical events: passed, 46 iterations, zero observed
BUSY/errors; p95 validation 817.07 ms, gate 690.27 ms, snapshot 118.48 ms. Retained report:
artifacts/soak-alpha-windows-20261020.json. Timings are fixture measurements with tracemalloc,
not production performance. Full 8-hour soak and native-process peak memory remain unmeasured.

M12d completed locally. Pinned openapi-typescript 7.13.0 / TypeScript 5.9.3, actual JSON Schema
validation, provider contract checks and loopback HTTP now run in a paired fixture. Baseline
catches the planted mismatch; zero additional detections claimed. Missing tools are unsupported,
and the wrong-field-type control fails the actual compiler. Node dependencies are fixture-only;
jsonschema 4.26.0 is now an explicit dev dependency already present in the locked environment.
Pilot kit writes zero observations/feedback and requires consent for actual pilot feedback.
Pricing-interest counts explicitly do not establish purchases or revenue. No volunteers ready.

| Final local alpha check | Executed result |
|---|---|
| Windows Python 3.12 full suite | 164 passed, 2 skipped in 284.56s |
| Linux Python 3.11 full suite, offline with verified Node 24.13.1 | 165 passed, 1 skipped in 67.55s |
| Linux Python 3.12 full suite, offline with verified Node 24.13.1 | 165 passed, 1 skipped in 71.93s |
| Actual bounded-filesystem-full Linux check | 1 passed in 0.21s on separate 4 MiB tmpfs |
| Fresh installed wheel, separate working directory, locked deps, CLI/MCP/onboarding/evaluator | 40 passed, 1 skipped in 31.09s |
| Installed CLI preview/apply/retry/doctor/next smoke | 5 steps passed; no preview state, duplicate task, accepted decision or next receipt |
| Whole-checkout Ruff lint/format and strict mypy | Passed; 97 files / 40 source modules |
| Lock / Python audit / optional npm audit | Lock check passed; 48 Python packages and 33 Node dependencies, no known findings at run time |
| CI syntax / distribution | Offline actionlint passed; source and wheel built and inspected; CI reports configured but no remote run |

Windows skips are symlink privileges and the separately executed bounded-filesystem drill.
Linux's one skip is that separate drill; actual Node/codegen/type/HTTP cases executed. Reports:
artifacts/alpha-final-windows312.xml, alpha-final-linux311.xml, alpha-final-linux312.xml, filesystem-full-linux312.xml,
alpha-installed-wheel.xml, onboarding-cli-alpha/report.json, alpha-npm-audit.json and
alpha-completion-distribution-check.json. Strong baseline retained study:
artifacts/pytest-alpha-final-windows/test_strong_baseline_paired_st0/study/.

CI now installs/explicitly requires the locked strong baseline, emits JUnit, verifies both
distribution archives, and retains reports/builds for seven days with a verified pinned official
upload action. Source-archive inspection caught nested node_modules inclusion; a root ignore
and rejecting check fixed it. Final artifacts are under artifacts/alpha-completion-dist (source about
227 KB, wheel about 85 KB). Wheel and sdist hashes are recorded. No tag, push or publication.
Dependency inventory remains metadata, not a completed third-party license/provenance review.
Remaining gates are explicit above; local completion does not approve stable release or benefit.

## M12a - product-value study tooling, completed 2026-10-20

- [x] Specify incremental-value positioning and matched baseline-plus-DecisionGuard protocol.
- [x] Add database-independent `evaluation schema/plan/report` CLI, strict typed study records,
  canonical plan digest, bounded relative evidence verification and explicit unknown outcomes.
- [x] Report baseline/additional detections, escapes with known downstream outcomes, benign
  blocks, paired timing/rework/overhead, setup failures and voluntary continuation feedback.
- [x] Preserve planned denominators/exclusions; reject duplicate, foreign-revision, altered-plan
  and tampered-evidence records. No automatic effectiveness/release approval or frequency claim.
- [x] Run real local baseline check + source-bound DecisionGuard runner/gate records through
  the reporting CLI. Both detect the planted unit mismatch; benign passes; zero incremental
  detections. Partial Python baseline only; downstream integration was not performed.
- [x] Add runnable pending study example and docs/PRODUCT_EVALUATION.md; update checkpoint.
- [ ] External M12: actual strong-baseline/competitor trials, volunteer pilot, live classifier
  evaluation and remaining operational/remote-release gates. M12a does not complete these.

Executed focused verification (not the full project matrix):

| Check | Result |
|---|---|
| Windows Python 3.12, new study + existing CLI/advisory evaluator regressions | 32 passed, 1 skipped in 19.08s |
| Linux Python 3.12, same selection in existing offline Docker image | 33 passed in 6.68s |
| Ruff lint / formatting, whole checkout | Passed; 83 files formatted |
| Strict mypy, whole src | Passed; 37 source files |
| Pending example CLI | Passed; missing arms exposed, zero eligible pairs, null rates |

The Windows skip is evidence symlink creation without developer-mode privileges; Linux ran
that rejection check. Docker used network none and read-only src/tests/examples mounts. Reports:
artifacts/product-evaluation-windows.xml and artifacts/product-evaluation-linux312.xml. The
Windows real-check study archive is under
artifacts/pytest-product-regression/test_actual_baseline_detection0/study/. No pilot participants,
competitor results, paid requests, remote CI results or product-effectiveness evidence were invented.

## Approved next phase - implementation started 2026-10-19

- [x] M7a: shared path/dependency relevance, predecessor scope, late-registration/scope notices,
  transactional notice deduplication. Focused lifecycle/notification suite: 10 passed.
- [x] M7b: service-backed benchmark, process ownership/cancellation, migration/session locks,
  backup/restore, archive and indexed history.
- [x] M8: reviewed OpenAPI artifacts, directional compatibility, bindings and portability v2.
- [x] M9: CLI/MCP impact, previews, watcher and installation diagnosis.
- [x] M10: opt-in previewed Jev advisories, isolated storage, no clearance authority.
- [x] M11: deterministic scenario expansion, TS/Python integration fixture and offline evaluator.
- [ ] M12: external competitor evaluations, paid classifier validation, volunteer pilot,
  remote CI and stable release gates. No effectiveness or production claims until measured.

This phase is sequential. No model calls, publication or live user database migrations are
authorized by merely running the offline tests. Explicit preview submission invokes Jev.

Implementation checks so far: 25 operations/process/CLI tests passed; 17 contract/portability/
real-MCP tests passed; 23 advisory/contract tests passed; TypeScript/Python loopback mismatch
and repair plus operations passed (4 tests). Diagnostic benchmark: 34/34 service-backed
classifications and 7/7 lifecycle checks in 99.5366s. These are planted fixtures, not sampled
production or live classifier accuracy. Full final verification is in progress; results below
from 2026-10-16 describe the previous version.

Remaining local depth gates: actual forced-process-death and disk-full recovery drills,
long-running soak, large-history performance measurements, archived event retention and
separate TypeScript type-checking. Optional live Jev measurement needs explicitly previewed
submissions, independently labelled data and a provider key. No such calls have been made.

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

## Next-phase verification - 2026-10-19

The unreleased local implementation is present; M12 and the local depth gates above are not
production clearance. Windows matrix runs collected 122 tests before the additional evaluator
duplicate-prediction regression; that new case and final path/resource/wire guards passed
subsequent targeted runs. The Linux final collection contains 123 tests. Targeted counts overlap.

| Check | Executed result |
|---|---|
| Windows Python 3.11 full suite | 122 passed in 665.73s |
| Windows Python 3.12 full suite | 122 passed in 639.40s |
| Linux Python 3.11, offline Docker | 122 passed, 1 skipped in 25.45s |
| Linux Python 3.12, offline Docker | 122 passed, 1 skipped in 26.68s |
| Final targeted classifier/evaluator/impact checks | 19 passed in 100.33s |
| Final selected-path and contract/advice checks | 28 passed in 70.64s |
| Final resolution/evaluator checks | 19 passed in 17.91s |
| Final backward-compatible finding details / lifecycle checks | 23 passed in 30.22s |
| Installed wheel, isolated environment outside checkout | 17 passed in 26.26s |
| Ruff / mypy | Passed; 76 formatted files, 34 typed modules; Linux mypy also passed |
| Service-backed diagnostic benchmark | 34/34 declaration classifications, 7/7 lifecycle; fixture-only |
| Lock / dependencies | Lock check passed; fresh OSV audit found no known issues in 48 packages |
| Distribution | Source archive and wheel built; packaged modules and canonical skill checked |

Linux images lack Node: their one skip is the optional TS/Python HTTP fixture, which executed
on Windows and verified baseline, actual 100x mismatch and repair. CI now installs pinned
Node 24 but has not been run remotely. No live model request or actual user-state migration
was performed. The inventory is not a completed third-party license/provenance audit.

Reports: artifacts/phase-next-release-windows312.xml, artifacts/phase-next-final-windows311.xml,
artifacts/phase-next-frozen-linux311.xml, artifacts/phase-next-frozen-linux312.xml and
artifacts/phase-next-installed-frozen.xml. Builds are in artifacts/next-phase-dist; dependency
inventory is artifacts/next-phase-dependency-inventory.json. No tag or package was published.

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
