# Protocol and implementation design — schema version 1

## Envelope and identities
All outputs contain `schema_version: 1`; errors contain `error: {code, message}`.
Lifecycle mutations require `actor`, `task_id` where task-scoped, and `idempotency_key`.
Local administrative init/migrate/prune commands use their explicit CLI inputs instead.
Server context determines project identity; no caller may select a foreign project.
Identifiers are bounded nonempty strings. Reject unknown request fields.
Contract identity is `boundary` + `key` within the current project.

## Values and lifecycle
Values contain `kind` (money_unit, time_unit, schema, auth, error_format, retry_policy,
idempotency, text), `value` (bounded string), and `deleted` (tombstone flag).
Decision versions store identity, version, value, scope paths, owner, rationale,
predecessor, evidence locations, timestamp. Proposals record an expected version
(0 means absent); status is pending, accepted, or rejected.
Review requires configured coordinator authority. Self-review is forbidden. Accepted versions
advance project revision and invalidate dependent evidence in one transaction.
Acceptance requires the active predecessor to match. A coordinator can explicitly reject a
stale losing proposal using its original expected version, without changing the active head.

Tasks store actor, worktree, registration baseline commit, declared paths, dependency versions,
and completed state. Changed-path coverage includes committed edits since registration,
staged/unstaged edits, and nonignored untracked files.
Assumptions store expected values, observed versions, and evidence locations. Explicit refresh
updates dependencies and observed versions but preserves expected values: implementation
must redeclare a changed expectation. No refresh or acknowledgement creates passing evidence.

Compatibility is equal, incompatible, or unknown. Equal typed values agree; unequal schema
or text is unknown. Unequal recognized categorical/unit values on the same boundary disagree.
Separate boundaries are independent. Coordinator-reviewed mappings can mark same-contract
values compatible or declare a cross-boundary conversion; mappings have rationale/evidence.

## Operations
CLI: init, status, context, task, assume, propose, review, events, ack, refresh, conflicts,
validate, gate, approve-task-scope, migrate, prune-receipts, export, import, demo, benchmark.
JSON request files carry structured mutation
arguments; stdout is stable JSON. Read options use task IDs, cursors, and limits (1–100).
MCP: get_context, register_task, declare_assumption, propose_decision, review_proposal,
poll_events, acknowledge_event, refresh_dependencies, list_conflicts, check_gate.
Mapping review is a coordinator CLI operation. MCP never accepts command strings.

Events have monotonic IDs, task recipients, type, proposal/contract/version metadata, and
timestamp. Poll returns at most 100 records after a cursor and records delivery. Acknowledgement
requires delivery and advances a durable cursor; it has no effect on evidence.
Error codes include INVALID, NOT_FOUND, FORBIDDEN, VERSION_CONFLICT, IDEMPOTENCY_CONFLICT,
BUSY, SOURCE_CHANGED, CONFIG_CHANGED, RESOURCE_LIMIT, and MIGRATION_REQUIRED.
CLI operational errors exit 2; blocked gates exit 1.

## Validation and gate

Database schema is now 2; protocol envelopes remain schema version 1. Tasks additionally store
`evidence_generation`, `run_sequence`, `latest_run_id`, `scope_revision`, and `scope_approved`.
Runs bind generation and sequence. Receipts include `evidence_runs` keyed by task ID.
Only the latest reserved run is eligible, even if a newer attempt fails or is interrupted.
Each evidence-invalidating mutation increments the task generation. Finalization cannot
resurrect an invalidated or superseded run. Gate source capture occurs outside write locks;
an entity-mutation epoch is checked before receipt publication. Receipts do not increment it.

MCP registration leaves scope unapproved. Local trusted CLI registration approves supplied paths.
`approve-task-scope` consumes actor, task_id, idempotency_key, paths, expected_scope_revision;
it requires current coordinator authority, increments scope revision and evidence generation,
and emits an event. Proposals must fit approved paths. Changes outside task paths block gates.
The integration task cannot be selected as an implementation task or share its worktree.

Optional config `limits` defaults: pending proposals 20/actor and 100/project; tasks 100/actor
and 1,000/project; snapshot 100,000 paths, 16 MiB of enumerated path names
(`snapshot_name_bytes`), 100 MiB/file, 1 GiB total, 60 seconds per capture.
Quota retries are checked before capacity; new writes check limits transactionally.
Limits fail closed with `RESOURCE_LIMIT`. Hashing streams in 1 MiB chunks.
Git path output is parsed incrementally and the producer is terminated on excess or timeout.
Non-Git enumeration prunes excluded/state directories and counts visited source directories
as paths too, so empty-directory trees cannot evade limits. Git limits apply to each raw
listing, conservatively including paths excluded later from hashing. Changed-path scans use
the same configured budgets. Administrative receipt pruning reports success after commit.

`migrate --sessions-stopped` creates a SQLite v1 backup and transactionally upgrades state;
old runs become invalid and old task scopes need approval. Never run migration beside old
CLI/MCP sessions. `prune-receipts --days 30 --keep 1000` explicitly removes older receipts,
retaining the newest 1,000 and all other history. Initialization preserves an identity journal,
uses a process-owned administrative lock and atomically replaces flushed config files.
Local config stores project identity/root, coordinator allowlist, runner argv/cwd/timeout/output
limit, optional task-specific `task_runners`, and optional snapshot exclusions. Paths must be relative and stay inside
the registered worktree. Run subprocesses with `shell=False`. No per-call command override.
Capture two identical manifests before running, then capture again after execution. Evidence
binds task, decision map, revision, config digest, source digest, actual exit status, and bounded
output. Relevant decision movement or source/config drift produces unusable evidence.

Gate input selects task IDs and optionally an integration task. Integration tasks require linked
isolated worktrees and the union of selected dependency contracts. Strict checks include missing
declarations and any changed tracked/nonignored path outside configured contract coverage.
Every selected task needs current passing runner evidence; integration needs separate evidence
for the combined source. Findings state task, boundary, expected/active values, rule, evidence,
and next action. A passing receipt records task/source maps and observed revision and is stored
durably. A later invocation recomputes freshness; receipts are point-in-time observations.

## Portability
Export accepted decision history, active heads, reviewed mappings, and provenance in versioned
JSON. Import only into an empty initialized project through coordinator review; retain origin
metadata but rebind to local project. Do not import tasks, command configuration, validation,
authority, event cursors, or passing receipts. CI registers its own integration task and validates.
