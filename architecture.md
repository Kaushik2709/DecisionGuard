# Architecture

## Components
`domain` owns validated request/value types, errors, and compatibility. `application`
owns lifecycle and gate services. `storage` owns SQLite transactions/migrations.
`git` resolves repository identity and validates worktree scope. `validation` captures
source and executes locally reviewed argv. `adapters` provides Typer and official SDK stdio.
`reports` contains deterministic evaluation; the demo creates real disposable worktrees.
Product studies use separate domain records, pure paired-report calculations, and an application
file-verification boundary. CLI evaluation commands need no project database and execute no
commands from study records. Study observations cannot change decisions, epochs or gate evidence.
Onboarding adapts explicit setup intent to the same initialization/registration services. Next-action
guidance uses the same gate calculation with receipt persistence disabled. Disposable reliability
workloads exercise real transactions and worktree workers; they accept only new fixture destinations.

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

## Unreleased schema 3 extension

Schema 3 adds immutable content-addressed OpenAPI artifacts, indexed task/event lookups and a
separate advisory_runs table. Advisory writes have no decision-revision or gate-epoch triggers.
No authoritative service reads advisory classifications when deciding compatibility or clearance.
Directional schema logic remains in domain; filesystem, database, CLI and MCP behavior remain
in application/adapters. Portable metadata v2 carries artifacts; v1 imports remain supported.

Service instances hold shared OS-backed activity leases for their lifetime. Migration and
restore acquire an exclusive lease after explicit stopped-session acknowledgement. Call close()
when embedding a service that must release its lease. Legacy versions do not hold these leases:
all old clients must still be stopped before maintenance. Migration never runs automatically.

Validation owns Windows children in a kill-on-close Job Object before resuming their suspended
primary thread. POSIX commands run in a new process group, cleaned in finally on success,
timeout or Python interruption. This is lifecycle control, not a hostile-code sandbox;
arbitrary POSIX daemon escape or forced supervisor death is not claimed to be contained.

Jev requests use the official TypeSafe endpoint and versioned model IDs, with a whole-request
10-second deadline and bounded response parsing. Preview never performs a request. Raw source
and the API key are not saved in advisory history; source hashes and typed results are retained.
CLI rendering of Codex configuration is preview-only; global client settings are never edited.
