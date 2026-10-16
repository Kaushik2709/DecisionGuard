# DecisionGuard product requirements

## Goal and users
Help developers using 2–4 coding agents in separate Git worktrees detect incompatible
declared decisions before integration. Clean file merges can still introduce semantic bugs.
Track contracts, assumptions, dependencies, reviewed changes, and evidence of revalidation.

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
AI, cloud, dashboard, vector database, or orchestration framework. Optional extraction is deferred.
Fixture benchmark results describe planted scenarios, not live-agent or production reliability.
