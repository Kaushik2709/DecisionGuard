# Project checkpoint

## Git ignore cleanup

Updated main and the automation implementation worktree ignore rules: local root `.codex/`
and `.agents/` stay private; `.env.*` variants are excluded while `.env.example` stays eligible.
Source, tests, lockfiles, CI and documentation remain eligible. No files were removed from
Git's index, and no commit or push was performed. Verification uses Git's own ignore checks.

## Controlled live two-session workflow completed - 2026-10-27

User explicitly approved consumer integration scope in the async question reply. Applied
the prepared reviewer CLI request: consumer scope revision 1, approved four transport
adapter/test paths; previous evidence invalidated. Rechecked source hashes against the
reviewed plan, backed up originals under pre-sync-backup/agent-two/, and synchronized its
two adapters plus MCP test environment-forwarding correction from integration. All four
selected paths are byte-identical across producer, consumer and integration worktrees.

Fresh consumer validation 7a37536d-afc0-4cdd-97cd-d6c3c658b799 finished passed/valid:
4 passed in 11.99s, one nonfatal pytest cache-permission warning. Producer run
5e25ccb1-176b-4100-bc1e-ffb6c6ece91e and integration run
b29d43b0-8c82-49e3-955e-1f714846c3e3 remained current and eligible.
Native MCP full gate selecting producer/consumer with transport-combined integration:
passed true, integration_checked true, findings [], revision 2. Receipt
cbe798ab-933b-4d06-86f6-21dfb940ade9. The same four tests ran against three worktree
states; do not claim twelve distinct tests or a fresh full-project matrix.

Completion report and actual receipt: artifacts/codex-repo-test-20261027/
completed-live-test-report.md and final-combined-gate.json. This completes the controlled
manual live workflow: proposal, MCP discovery, pending block despite passing tests,
acceptance, stale/conflicting evidence, real failing consumer tests, reviewed combination,
scope approval, synchronization and fresh passing combined gate. Main application source
remains unchanged; scenario edits are only in test worktrees. No merge to main, push or
publication performed. Production reliability/general effectiveness remain unproven.
Earlier pending-approval/block sections below are historical, superseded by this result.

## Producer synchronized; consumer scope approval requested - 2026-10-27

User asked how to resolve the remaining block. Verified v2 still active and reviewed
the retained synchronization plan. Synchronized the two strengthened transport tests
(including the MCP PYTHONPATH forwarding correction) into agent-one within its existing
four-file approved scope. Original files retained under pre-sync-backup/agent-one/.
Main application source unchanged. Fresh producer validation
5e25ccb1-176b-4100-bc1e-ffb6c6ece91e passed/valid: 4 passed in 12.00s.
Full gate now blocks only consumer missing_or_stale_evidence and combined_source_mismatch.
Artifacts: producer-source-sync.json, producer-combined-validation-result.json and
gate-after-producer-sync.json in the same test directory.

Asked through async user input for explicit approval to add the two producer adapter
paths to transport-consumer's existing two-test-file scope. Tool acceptance only means
the question was presented, not user approval. Await an actual user answer before
applying approve-consumer-integration-scope.json or copying adapters to agent-two.
After approval, apply that request through reviewer CLI, verify the three remaining
consumer source hashes against remaining-combined-validation-plan.json, back up and
copy those reviewed files from integration, validate consumer with a fresh key, then
rerun the full gate. Existing producer and integration evidence may be reused if still
current. No main merge or publication is authorized by this local test.

## Accepted v2 and combined-source preflight - 2026-10-27

User supplied screenshots showing the coding sessions had advanced: the existing change
proposal was accepted through the trusted reviewer CLI in agent one's session. Native MCP
verified active v2 / revision 2, code,message,retryable. Producer changed only its two
adapters and passed its four-test validation. Consumer updated only its two transport tests,
redeclared v2 and got the expected three failures against its still-old producer. No new
contract acceptance was performed by this observer turn.

Reviewed the four diffs and assembled them only in the pre-existing clean integration worktree;
both coding worktrees and main application source were preserved. Declared integration v2
through the trusted CLI. First configured combined validation: 3 passed/1 failed because the
SDK filters inherited PYTHONPATH and the MCP test subprocess imported main's old adapter.
This exposed a gap in our worktree runner claim, not a reason to weaken the new assertions.
Verified installed official SDK behavior and v1.x source. Added explicit conditional PYTHONPATH
forwarding to StdioServerParameters.env in integration/tests/transport/test_mcp.py only.
This preserves installed-wheel/default behavior when the variable is absent. The correction
has not been applied to main or either coding worktree; retain it when integrating changes.

Fresh configured integration validation b29d43b0-8c82-49e3-955e-1f714846c3e3: 4 passed
in 12.09s, passed/valid true. Selected four-file Ruff/format passed. Separate real MCP
startup-error smoke passed with schema_version 1, INVALID code, nonempty message and
retryable false. Full multi-task gate still blocks: consumer missing_or_stale_evidence plus
combined_source_mismatch for producer and consumer; integration_checked true.

Prepared remaining-combined-validation-plan.json: producer needs the two strengthened tests;
consumer needs the two new adapters and the MCP environment-forwarding correction. Consumer
still has only its two test paths approved. Obtain explicit user approval for the prepared
approve-consumer-integration-scope.json before copying adapter files into that worktree.
After approval, verify all source/target hashes against the plan, apply only those reviewed
copies, run fresh producer/consumer validation and retry the combined gate. Integration's
passing evidence can remain eligible if its source/config/contract have not changed.
Do not approve scope or import source silently. Do not merge main or claim full test completion.
Artifacts under artifacts/codex-repo-test-20261027/: combined-source-manifest.json,
combined-validation-first-attempt.json, combined-validation-result.json,
integration-harness-fix.patch, combined-startup-error-smoke.json,
combined-gate-before-scope-approval.json and remaining-combined-validation-plan.json.

## Live Codex proposal delivery verified - 2026-10-27

User supplied screenshots from the two actual Codex coding sessions. Verified against native
MCP context/impact and fresh separate task gates plus read-only DB inspection: agent one
submitted proposal `3acef40e-82d0-47b1-8d8e-8db8b3085488`, expected version 1, changing
required_fields from code,message to code,message,retryable (boolean false initially).
Agent two received matching pending_impact event 9; its delivery cursor is 11 and ack is 5.
Both declared baseline assumptions and have current finished/passing/valid validation:
producer 4 passed (13.35s), consumer 4 passed (13.22s) with a nonfatal pytest cache permission
warning. Both fresh scoped gates block solely on pending_impact despite that passing evidence.
Both worktrees have no source edits. Baseline remains active v1 / revision 1; new proposal
is pending and has not been approved. This demonstrates the controlled live two-session
MCP polling path, not automatic wakeup, code adaptation or combined-source success.
Reports: live-two-session-check.json and live-gates-check.json under the test artifact root.
Next: explicit user review of the retryable-field proposal, then code/test adaptation,
fresh validation and actual combined-source gate. Do not reuse baseline approval for it.

## Same-repository baseline accepted - 2026-10-27

User explicitly approved the prepared baseline. Trusted local CLI reviewer accepted proposal
`e7e4614c-43f7-47b8-bbe8-71b979ac7756` with the prepared idempotency key. Project revision 1;
`decisionguard.transport.error::required_fields` version 1 is error_format `code,message`.
Native MCP get_context verified the active version. Read-only database inspection verified
accepted events 4/5/6 queued for producer/consumer/combined; no agent delivery cursor advanced.
Artifacts: baseline-review-result.json and baseline-acceptance-check.json under
artifacts/codex-repo-test-20261027/. This accepts the existing baseline only, not a future
retryable-field change, implementation completion or gate clearance. Next: open agent two
then agent one at their prepared worktrees and paste their existing prompt files. Actual
two-Codex-agent coding/adaptation and combined-source validation remain outstanding.

## Same-repository two-session MCP setup - 2026-10-27

User clarified that the test must use this actual repository, with separate coding
sessions discovering changes through DecisionGuard MCP. Initialized shared state at
`D:\DecisionGuard\.git\decisionguard`; project `57b495cc-15f6-4259-a882-c9c12ca99e29`,
coordinator `reviewer`. Main MCP now points here as ordinary `repo-observer` and native
get_context/list_conflicts work in this chat. The earlier sandbox is retained separately.

Prepared linked agent-one, agent-two and integration worktrees under
`artifacts/codex-repo-test-20261027/`, from detached snapshot commit
`30bb8885d92ba2b943e1e52f9ed829916f03bcc4` of current working source. Main HEAD/index and
original source bytes were verified unchanged before this checkpoint update. Nothing pushed.
Each worktree has its own actor-bound project config and canonical workflow skill; its
snapshot ignores machine-local .codex/.agents folders. Codex discovery verifies actor/root
pairs. Existing tasks: transport-producer (agent-one; broad four-path proposal scope),
transport-consumer (agent-two; two transport test paths), transport-combined (integration).
The reviewed runner loads each worktree's src in parent/child Python and runs the two
transport test modules. Default Windows temp permissions failed preflight; switched to a
fresh UUID basetemp under each worktree's ignored artifacts folder. Final preflight: 4 passed
in 12.12s. This is selected runner evidence, not a new full suite or a gate clearance.

Two real SDK stdio clients (not LLM coding sessions) verified shared project identity,
13 tools each, producer proposal -> consumer pending_impact event 2, and blocked consumer
gate. Baseline proposal `e7e4614c-43f7-47b8-bbe8-71b979ac7756` remains pending: current
CLI/MCP error fields code,message, typed error_format, scoped to both adapters and both
transport test modules. Zero accepted decisions. Explicit owner review is still required;
do not accept it or the later retryable-field proposal silently. Review request, two agent
prompts, validation helper, scope-expansion request, RUNBOOK.md and actual smoke reports are
under the artifact directory. Live Codex agent compliance/adaptation is still unmeasured.
Current chat can observe MCP state; open coding sessions at the exact worktree folders.
Polling is explicit; there is no automatic chat delivery, agent wakeup or background polling.

## Codex MCP connection - 2026-10-27

User requested adding the Codex configuration. Added project-local `.codex/config.toml`
with ordinary actor `frontend`, using the existing project interpreter and disposable pilot
root `artifacts/codex-pilot-8c49f414/repository`. The main repository has no initialized
DecisionGuard state; only the new pilot was initialized, with coordinator `reviewer`, no
registered tasks and no accepted decisions. Existing global Codex settings were preserved.
Codex `mcp list --json` discovers the enabled entry. Real SDK stdio initialization, all 13
tools and `get_context` passed; the pilot conversion test passed (1 test). Connection report:
`artifacts/codex-pilot-8c49f414/connection-check.json`. Restart/reconnect Codex to expose tools
in a new session; interactive multi-agent workflow compliance has not been tested.

## Different-case verification - 2026-10-21

User asked to check different cases after clarifying the demo's intentional failing application.
Reran the actual benchmark: 34/34 expected classifications, 16 conflicts blocked, 12 clear,
6 unknown/blocked; all 7 lifecycle checks passed, including real competing reviews. Runtime
97.088s. Then ran 64 selected lifecycle/freshness/worktree/concurrency/impact/combined-source/
OpenAPI/strong-baseline/hardening checks: all passed in 182.32s, no skips. Do not call this a new
full-suite Windows/Linux matrix or production/live-agent effectiveness evidence.

Added only tests/integration/test_semantic_case_boundaries.py, with two meaningful controls:
1. Explicit reviewed major-to-minor conversion: correct code passes; broken code makes old
   evidence stale, fresh configured assertion fails and gate stays blocked; repair/revalidate passes.
2. Known limit: unchanged declarations and a weak nonempty assertion allow a deliberately
   undeclared unit/business mismatch (4,990,000 vs expected 49,900) to pass the gate. This is an
   intentionally confirmed coverage limitation, not a caught bug or product-defect remediation.

Evidence: artifacts/case-validation-20261021/report.md, summary.json, benchmark.stdout.json and
cases-windows.xml, plus retained conversion/negative-control JSON in the pytest subdirectory.
New test formatting/lint passed. No core behavior, real user state, settings, main-repository
commits/pushes or publication changed. Preserve all earlier dirty implementation work. Continue
to explain that declared disagreements and fresh configured tests are enforced, while undeclared
business behavior is not automatically inferred. Existing pilot/release/soak gates remain open.

## Product alpha local milestones completed - 2026-10-20

M12b/M12c/M12d are implemented and verified locally. User confirmed nobody is ready for a pilot;
do not invent volunteer, adoption, willingness-to-pay or live-agent effectiveness evidence.
No publication, remote CI, commits/pushes, real user-state changes or global setup edits occurred.

New workflows: `setup project <request> [--apply]`, `next --task-id ...`, improved doctor,
`reliability recovery/soak/filesystem-full`, `evaluation kit`. See docs/ALPHA_WORKFLOW.md.
Setup is preview-first/resumable and accepts no decisions. Next uses the actual current-source
gate with receipt persistence disabled. Doctor diagnoses missing task overrides and cwd.
Actual killed-writer rollback, lost-response retry, backup restoration and real bounded-disk
exhaustion passed; SQLite page-ceiling and physical filesystem-full drills remain distinct.
The 30-second two-worker/10,000-event fixture passed but eight-hour/native-RSS gates stay open.

examples/strong-baseline has pinned npm lock/codegen/strict TypeScript plus JSON Schema,
provider contracts and actual Python/Node HTTP. Both arms catch the planted unit mismatch;
zero incremental catches claimed. Wrong field type fails the real compiler. Missing tools
are unsupported; CI sets DECISIONGUARD_REQUIRE_STRONG_BASELINE=1 so missing tools fail there.
jsonschema 4.26.0 is an explicit dev dependency; no locked package versions changed. Pilot
feedback adds consent and optional pricing interest/budget; reports say stated interest only.
The generated kit at artifacts/alpha-pilot-kit-20261020 is an empty fixture, not a live pilot.

Full Windows Python 3.12: 164 passed/2 skipped (284.56s). Full Linux Python 3.11:
165 passed/1 skipped (67.55s). Full offline Linux Python 3.12 with
checksum-verified Node 24.13.1: 165 passed/1 skipped (71.93s). Linux skipped only the separate
bounded-filesystem test; that ran on its own 4 MiB tmpfs and passed (0.21s). Windows additionally
skipped symlink creation due privileges. Fresh, hash-locked installed-wheel environment outside
source working directory: 40 passed/1 skipped (31.09s), including actual MCP transport. Separate
installed CLI smoke covered preview/apply/retry/doctor/next, with zero preview writes, duplicate
tasks, accepted decisions or next receipts. Whole-checkout Ruff/format and strict mypy passed
(97 files, 40 source modules), lock and actionlint passed; fresh audits found no known issues in
48 Python packages / 33 optional Node dependencies. No stable/security certification is implied.

Artifacts: alpha-final-windows312.xml, alpha-final-linux311.xml, alpha-final-linux312.xml,
alpha-installed-wheel.xml, filesystem-full-linux312.xml, alpha-npm-audit.json,
alpha-completion-distribution-check.json and onboarding-cli-alpha/report.json under artifacts/.
Final wheel/source are in alpha-completion-dist; prior checked builds remain separately retained.
Wheel SHA256 f204cdd6d3fe8d936f98560ed20871161d945da76d6f098c63349943580a57d5.
Packaging inspection caught nested node_modules in the sdist; root .gitignore now excludes it
and scripts/verify_distribution.py rejects local state/dependencies in both archives. Source
shrunk to ~227 KB. CI retains test/build reports but has not run remotely on these changes.

Linux verification initially lacked xz CLI, executable Node tmpfs and the workflow-skill mount.
Used Python tarfile, explicit exec tmpfs and read-only skills mount, then the full suite passed.
An offline fresh-env attempt lacked some dev wheels; downloaded exact hash-locked versions into
the workspace cache. All these were test-environment setup corrections, not passing test evidence.
Python 3.11 Linux full verification also passed. External gates remain real pilots,
competitor trials, full-duration soak, optional classifier evaluation, remote CI and owner-controlled
private reporting/publication plus dependency license/provenance review. Preserve existing dirty work.

## Product alpha improvements in progress - 2026-10-20

User requested implementing the remaining product improvements. No volunteers are available
(explicit user reply); prepare pilot materials, never invent adoption or pricing evidence.
Sequential scope and acceptance gates are at the top of tasks.md. Existing dirty work preserved.

M12b implemented: `setup project <request> [--apply]` previews validated worktree/task intent by
default; explicit apply initializes/registers tasks with deterministic retry keys. Existing
runner/coordinator configuration is preserved. Partial setup can resume; missing contracts are
not auto-published or accepted. `next --task-id ... [--integration-task ...]` performs current-source
gate assessment with record_receipt=False and orders original findings without hiding them.
It changes no evidence, assumptions or decisions; exit 1 means blocked. `doctor` now diagnoses
task-specific runner overrides and invalid/missing cwd, and exits 1 when not ok.

Focused Windows onboarding/operations/setup tests: 9 passed (initial 13.50s); final rerun report
artifacts/onboarding-windows.xml. Ruff passed, mypy passed for 39 modules. M12c recovery/drill and
performance tooling and M12d baseline/pilot/release checks remain in progress. No actual user
database initialized or migrated, global settings changed, or remote publication performed.

M12c completed locally: `reliability recovery <new-dir>` kills a real review process before
commit and after commit, checks rollback/idempotent lost-response retry, observes SQLite FULL
under a page-count ceiling, and restores a real backup with invalidated evidence/history intact.
`reliability filesystem-full <new-dir>` refuses ordinary filesystems; only <=16 MiB POSIX
filesystems qualify. Separate offline Linux test used 4 MiB tmpfs and verified physical storage
exhaustion, rollback/history preservation and successful writes after freeing fixture filler.
`reliability soak <new-dir> --seconds ... --workers 2..4 --history ...` seeds bounded synthetic
events and runs actual linked-worktree worker processes through validation, gates and snapshots.
It reports p50/p95, errors/BUSY/state-change counts, state sizes, Python tracemalloc peaks and
quiescent final gates; process RSS is honestly unknown. All paths must be new disposable roots.

Windows drill tests 7 passed/1 skip (10.69s); Linux bounded-full test 1 passed (0.21s). Windows
30-second, two-worker, 10,000-history-event measurement passed, 46 iterations, no BUSY/errors;
p95 validation/gate/snapshot 817.07/690.27/118.48 ms. Full 8-hour gate remains false. Report:
artifacts/soak-alpha-windows-20261020.json; JUnit reliability-windows.xml and
filesystem-full-linux312.xml. M12d baseline/pilot/release work is next. Official OpenAPI codegen
and TypeScript CLI docs checked before using those tools. No volunteers or live agent benefit
results are available; user explicitly said no one is ready.

## M12a product-validation tooling handoff - 2026-10-20

User requested implementing the product-requirements milestone after discussing schema/test
overlap, narrow audience, missing frequency data and platform risk. Implemented a concrete
offline evaluation slice; external M12 remains uncompleted, not replaced by fixture arithmetic.

New domain/product_evaluation.py holds strict study plans and observations; reports module
computes descriptive matched-pair metrics; application module verifies bounded local files.
CLI `evaluation schema`, `evaluation plan <plan.json>` and `evaluation report <plan.json>
<observations.json>` require no initialized state and execute no supplied commands. They never
change decisions, evidence or gate authority. Plans bind sources, participants, baseline check
configuration and success criteria by canonical SHA-256. Altered/missing logs, changed plans,
duplicate runs and unplanned/mismatched observations fail explicitly. Unknowns are not success.

Reports credit baseline detections, additional and baseline-only detections, known downstream
escapes, benign blocks, timings/rework/overhead, setup failures and voluntary feedback. Explicit
denominators/exclusions and fixture/provenance limits remain visible. No report approves a
release/effectiveness claim or estimates population frequency. Hashes cannot prove measurements,
independent review or preregistration. See docs/PRODUCT_EVALUATION.md and the pending, empty
examples/product-study archive. Its label bytes are pinned LF with a targeted .gitattributes rule.

Windows Python 3.12 focused new study + existing CLI/advisory evaluator regressions: 32 passed,
1 skipped (19.08s); same offline Linux Python 3.12 selection: 33 passed (6.68s). Windows lacks
symlink creation privileges; Linux executed that test. Ruff lint/format passed for whole checkout
(83 files), strict mypy passed (37 source modules). These are focused checks, not a new full-suite
matrix. JUnit reports: artifacts/product-evaluation-windows.xml and product-evaluation-linux312.xml.

Real local test retained a fixed plan plus actual baseline Python assertion outputs and actual
DecisionGuard runner/gate records; mismatch caught by both, benign passes both, zero incremental
discoveries. This is a partial Python baseline, not schema/codegen comparison, live agents or a
separate downstream integration. Escaped-defect rates remain unknown. Archive:
artifacts/pytest-product-regression/test_actual_baseline_detection0/study/.

Preserved the substantial pre-existing uncommitted M7-M11 work. No live project-state changes,
global settings edits, new dependencies, model calls, outreach, commits, pushes or publication.
Next product step: execute preregistered matched tasks with the full existing-tool baseline and
real developers; measure adoption and net benefit. Existing operational/remote-release gates
in tasks.md and docs/ADVISORY_EVALUATION.md still apply.

## Unreleased next-phase handoff - 2026-10-19

M7-M11 local features are implemented and documented. Remaining production gates are explicit
in tasks.md and docs/ADVISORY_EVALUATION.md: independent/live Jev evaluation, competitor trials,
8-hour soak/large-history/actual failure drills, private reporting and release configuration,
volunteer pilot and naming/publication. No portal, automatic agent wakeup or A2A adapter exists.

Windows full suites: Python 3.11 122 passed (665.73s), Python 3.12 122 passed (639.40s). Final
Linux 3.11 122 passed/1 skipped (25.45s), Linux 3.12 122 passed/1 skipped (26.68s), with 123 tests
collected after one evaluator test was added. Final focused guards passed (19, 28 and 19 tests;
overlapping runs), and installed-wheel CLI/MCP/setup/advice/evaluator tests outside checkout
passed (17, 26.26s). Linux skip is Node-dependent HTTP fixture; Windows ran it. Subsequent
wire-compatibility check preserves evidence locations and adds pointer reasons under details.

Ruff (76 files), strict mypy (34 modules; Windows/Linux), lock check and fresh dependency audit
passed (48 audited packages, no known findings at the time). Source archive/wheel are under
artifacts/next-phase-dist. Wheel force-includes the canonical root workflow skill and setup
preview can read it outside a source checkout. A dependency inventory exists but license review
is incomplete. CI adds a verified pinned setup-node v6 commit for Node 24 and builds artifacts;
remote CI was not triggered. See tasks.md for report filenames and evidence boundaries.

No real user database initialized/migrated, global Codex settings changed, live Jev requests,
commits, pushes or publication. Root remains the user's Git repository on main. Jev credentials
are never reused from other projects; tests use fake keys and httpx MockTransport. Core gates
do not consult advisory rows; no classifier outcome can accept or clear work.

## Next phase in progress - 2026-10-19

Implementing the approved deterministic foundation plus optional advisory-only Jev plan.
The workspace now has a Git repository on main at f77ff52 (user's first commit); it was clean
at entry. Preserve this repository; no commits, remote changes or publication requested.
M7a notification parity/old scope/bootstrap/deduplication implemented; 10 focused tests passed.
Runner job ownership implementation additionally passed 17 lifecycle/freshness tests. Broader
process-tree regressions and schema 3 work are in progress. No live model requests or user
database migrations have been performed. tasks.md tracks remaining milestones and external gates.

M7b-M11 local implementation is now present: schema 3 backed-up migration with shared-session
leases; Windows suspended launch/Job Object and POSIX finally cleanup; archive/restore,
backup/restoration that invalidates a staged copy before replacement; directional OpenAPI
artifacts and metadata v2; CLI/MCP previews/impact/read-only advice; explicit optional Jev
API with bounded preview and response, 10-second overall deadline, pinned model, idempotent
submission and separate advisory table. No advice influences revisions, epochs or gates.
Official OpenAPI, TypeSafe and Codex configuration docs checked. Codex setup only prints TOML.
Live model API was not called; tests use httpx MockTransport. Shared-lock testing caught and
fixed Windows msvcrt's inability to provide the required shared leases using LockFileEx.
New test Git ceilings isolate fixtures from the real parent repository. Backup staging uses
explicit SQLite close (connection context managers alone retain Windows file handles).

TypeScript/Python HTTP fixture executed successfully: 499 rupees -> 49900 provider paise;
frontend-only 49900 change produces 4990000 mismatch; backend repair passes. Node 24.13.1
is available locally; no npm dependency required and no TypeScript type-check claimed.
Benchmark now runs 34 declaration scenarios through services, reviews, runner and actual
gate; 34/34 and 7/7 lifecycle passed in 99.5366s. Not live-agent/model or production evidence.
Final Windows/Linux regression and installed-wheel checks are underway. Docker access uses
the existing offline images with read-only source mounts and results under artifacts.

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
