# DecisionGuard product requirements

## Goal and users
Help developers using 2–4 coding agents in separate Git worktrees detect incompatible
declared decisions before integration. Clean file merges can still introduce semantic bugs.
Track contracts, assumptions, dependencies, reviewed changes, and evidence of revalidation.

Product positioning: coordinate reviewed contracts and fresh validation across parallel coding
worktrees. Complement shared schemas/codegen and contract/integration tests. Automatic discovery
of undeclared semantic disagreements and proof of whole-repository correctness are not promised.

## Workflow
Initialize shared state; establish contracts through proposals and explicit review; register
tasks and worktrees; retrieve context and declare assumptions; propose changes; inspect impacts;
review; poll events; acknowledge; refresh dependencies; correct code; validate; check the
actual combined source in an isolated integration worktree.

## Requirements
- Distinguish delivery, acknowledgement, refreshed knowledge, and validated implementation.
- Immutable contract versions keyed by project/boundary/key, with typed values and tombstones.
- Deterministic compatibility for declared values; reviewed conversions between boundaries.
- Durable events, concurrency-safe review, idempotent mutations, and restart persistence.
- Shared CLI/MCP services; only local CLI runs reviewed validation commands.
- Strict scoped gates fail closed on conflict, relevant pending proposals, stale knowledge,
  missing/stale/failed evidence, and unknown changed-path coverage.
- Portable reviewed metadata for CI; imported evidence must be regenerated.
- No API key is needed for any v1 functionality.
- Only the latest validation attempt can clear a task; failed or unfinished later attempts block.
- Refresh/assumption/scope changes invalidate in-flight evidence through a task generation.
- Changed files must fit approved task paths; integration tasks/worktrees must be distinct.
- Support recoverable setup, backed-up explicit migration, bounded snapshots and proposal quotas.

## Acceptance
The disposable checkout demo starts with public decimal major units and integer provider
paise. A public change to paise merges cleanly but produces a real 100× mismatch. Pending
impact is visible, acceptance invalidates evidence, acknowledgement remains blocked,
and corrected code plus fresh task/combined validation passes. A rejected public change
with an explicit internal conversion also passes.

## Boundaries
V1 trusts the same local user. It neither orchestrates agents nor merges branches nor proves
whole-repository correctness. Independent clones need explicit metadata transfer. No mandatory
AI, cloud, dashboard, vector database, or orchestration framework. Model-driven automatic
contract extraction remains outside scope; reviewed OpenAPI imports are explicit.
Fixture benchmark results describe planted scenarios, not live-agent or production reliability.

## Next-phase capabilities (unreleased, 2026-10-19)

Target the TypeScript-client/Python-API workflow with reviewed OpenAPI 3.1.x JSON imports,
explicit unit templates and conservative directional compatibility. Supported request changes
must continue accepting old client inputs; response changes must fit declared consumer
expectations. Unsupported schema behavior is unknown, including unchanged unsupported artifacts.
Scanning is read-only; publication creates pending proposals and never accepts them.

Optional Jev classification is advisory only and disabled until explicitly invoked through the
local CLI. It receives only a bounded, previewed selection of diffs and accepted contract values.
No background model calls, automatic retries, automatic approvals or model-created validation.
An unavailable or negative classification cannot resolve deterministic findings. Live classifier
accuracy and competitive benefit require the independent evaluation/pilot in docs/ADVISORY_EVALUATION.md.

The portal, agent conversations, automatic wakeup and A2A integration are not implemented.
Producer/consumer labels provide reviewed context; agents still declare their own dependencies
and implementation assumptions. No process can force an independent coding agent to comply.

## M12a - incremental product-value evaluation (2026-10-20)

Provide an offline, database-independent paired-study CLI before claiming product effectiveness.
Freeze the study question, source cases, participants, baseline configuration and success criteria
in a digest-bound plan. Compare identical starting source under a documented baseline and that
baseline plus DecisionGuard. The full target baseline includes schema validation, codegen,
contract tests and integration tests; partial baselines must be labelled explicitly.

Report early detection, downstream escaped defects, detection/elapsed/rework/tool time, benign
blocks, setup effort including failures, and voluntary continuation feedback. Credit cases already
caught by the baseline. Preserve unknown labels/outcomes, missing measurements and unavailable
tool runs; expose all planned pairs and each exclusion. Repeated participant runs are not distinct
independent source changes. A planted mismatch establishes possibility, not incident frequency.

Acceptance: local CLI can inspect a plan, expose its schema, verify relative evidence files by
SHA-256, reject altered plans/logs and mismatched/duplicate observations, and emit a reproducible
descriptive report. A real local baseline/check and DecisionGuard gate fixture must show baseline
credit on a mismatch plus a benign case. No report can approve a release or confer gate authority.

External M12 remains open: independently reviewed representative matched tasks, real 2-4-agent
workflow pilots, competitor runs, adoption and net-benefit review against preregistered criteria.
Evidence hashes attest file consistency, not measurement truth, reviewer independence or genuine
preregistration. No telemetry, model calls, outreach or publication is part of M12a.

## Product alpha improvements (2026-10-20)

Reduce initial setup to a reviewed project request with default preview and explicit resumable
apply. Show ordered next steps from a fresh assessment without recording a clearance receipt or
changing dependencies. Diagnose all configured task runners, not only the default command.
Preserve manual review, declared coverage and current-source validation requirements.

Provide reproducible local failure and performance drills plus a real strong-baseline fixture
and a pilot kit. Actual killed-process, capacity-limit and bounded-filesystem failures must be
distinguished; short soak runs never stand in for eight hours. Record real uptake and pricing
interest only from consenting participants. No volunteers are available at this milestone;
customer validation remains pending. Release checks produce reviewable artifacts; publication
and remote checks require their own actual evidence.
