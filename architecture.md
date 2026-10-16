# Architecture

## Components
`domain` owns validated request/value types, errors, and compatibility. `application`
owns lifecycle and gate services. `storage` owns SQLite transactions/migrations.
`git` resolves repository identity and validates worktree scope. `validation` captures
source and executes locally reviewed argv. `adapters` provides Typer and official SDK stdio.
`reports` contains deterministic evaluation; the demo creates real disposable worktrees.

## State and concurrency
Use `<absolute git common dir>/decisionguard/state.db` and adjacent `config.json`.
Linked worktrees share state; independent clones do not. Non-Git projects require explicit
project root and state directory. State must be on a local filesystem supporting SQLite WAL.
SQLite enables foreign keys, WAL, bounded busy handling, and immediate write transactions.
Every mutation has project/actor/task scope and an idempotency key; review also checks
the exact predecessor. Publish, revision increment, invalidation, events, and retry result
commit together. Published versions are never edited. Active heads are separate records.

## Trust
Coordinator actors and runner commands come from local configuration. Authority is reloaded
on mutations, including cached retries; removal applies to newly authorized requests in
already-running sessions. Configuration identity changes require a verified restart.
An agent cannot grant itself authority through a role field or invoke a runner through MCP.
CLI validation creates runner evidence through an internal application interface. This is a
same-user coordination boundary, not protection against local config/database tampering.
The CLI is a trusted local operator channel. Fixed-actor MCP sessions enforce ordinary-agent
restrictions. Unrestricted shell/filesystem access can impersonate the local operator; this
tool does not sandbox agents running as the same OS user.

## Decisions
- ADR-001: SQLite plus the Git common directory provides one local state for linked worktrees.
- ADR-002: Unknown compatibility is distinct from confirmed contradiction and blocks strict gates.
- ADR-003: Source digests include all tracked and nonignored untracked files, and deletion markers;
  validation config can exclude generated output but exclusions are explicit and hashed.
- ADR-007: Database v2 adds evidence generations, latest-run sequence/pointer, scope approval,
  and a transactional state epoch. Snapshot work stays outside the gate writer transaction;
  the epoch is rechecked before committing a point-in-time receipt.
- ADR-008: MCP-created scope requires coordinator CLI approval. Trusted local CLI registration
  explicitly approves its supplied scope. Proposal scope cannot exceed approved task scope.
- ADR-009: Initialization journals its intended identity and atomically publishes configuration
  under an OS-backed lock. Explicit v1 migration requires stopped sessions and a SQLite backup.
- ADR-004: Integration is a registered isolated worktree containing user-prepared combined source.
  The service never merges. CLI checking and a subsequent Git merge are not atomic.
- ADR-005: Pin official MCP SDK to the maintained v1 API (`mcp<2`) and test its real stdio transport.
- ADR-006: Six canonical specifications own requirements; avoid parallel duplicated docs.

## Limitations
Coverage is declared, not inferred from code. Files ignored by Git are outside snapshots unless
tracked; secrets must not be declared as evidence. Tests cannot prove arbitrary architectural
prose. Polling is manual at documented checkpoints, and skills cannot guarantee compliance.
Pre/post digests detect persistent changes, not a malicious edit-and-restore during execution.
