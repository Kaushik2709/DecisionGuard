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

Database schema is now 3; protocol envelopes remain schema version 1. Tasks additionally store
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

## Unreleased extension interfaces

- CLI: contracts scan/propose, impact, watch, doctor, archive-task, restore-task, backup,
  restore-backup, maintain, setup codex, advice preview/classify/list/evaluate.
- MCP adds preview_contracts, explain_impact and list_advisories to the ten existing tools.
  Preview requires the bound actor's approved task scope. No MCP tool invokes Jev or runners.
- ContractScan: task_id, spec (worktree-relative JSON path), bindings. Each binding contains
  method, path, direction (request/response/security), response status, contract identity and
  scope; optional producer/consumer IDs and field templates (schema JSON pointer + typed value).
- ContractPublish: actor, idempotency_key, scan, preview_digest, expected_versions, rationale.
  The batch is atomic and retries return its prior result even after review. Each proposal is
  subsequently reviewed separately. Schema Values remain digest strings; new records do not
  change the legacy Value wire shape.
  Schema pointer explanations use an additive findings.details field; findings.evidence keeps
  its existing location-list shape for compatibility.
- AdviceRequest: task_id, pinned model, 1-5 candidates (contract + selected paths), attempt=0.
  Preview contains the exact outbound payload and local source/contract identity. classify
  accepts that saved preview; changed or modified previews fail. Increment attempt only for a
  deliberately new submission. Advice has possible_contract_impact/no_impact_indicated/
  insufficient_context labels, probabilities and confidence. It has no acceptance authority.
- Advisory status: submitting, available, unavailable, stale; a surviving submitting record
  is presented as submission_outcome_unknown. Reusing a preview never resends it automatically.
  classify exits 2 for unavailable/stale/indeterminate outcomes. Provider latency and reported
  token usage are retained without inferring billed cost. Evaluation rejects duplicate case IDs,
  reused prediction/candidate pairs and development/held-out repository/family leakage.

New input bounds: CLI JSON request 16 MiB; OpenAPI source/selected preview 10 MiB; 100 selected
operations; resolved selection depth 64, 50,000 nodes and 128 KiB text; advice outbound 32 KiB,
16 KiB per selected/baseline file and response 64 KiB. Resource exhaustion fails explicitly.
Same-document references are bounded; remote/cyclic/composed/unsupported semantics stay unknown.

Relevant notices use dependencies and the union of predecessor/current/proposed paths. New
tasks, dependency declarations and scope expansions bootstrap accepted_context and pending_impact
events; notice keys deduplicate within the mutation transaction. Poll/ack semantics are unchanged.
Task context includes accepted decisions relevant by dependency or path without automatically
declaring new dependencies. Impact explains evidence metadata but explicitly leaves source
freshness to a gate check. The resolution node/text budget is shared across the entire scan.

Archival retains history and frees active quotas; restore requires capacity and invalidates
evidence. maintain previews old non-latest run-output removal by default, preserving decisions,
events, retries and latest evidence. Event expiration is not implemented. Restore stages invalid
evidence before replacing live contents, retains a rollback backup and preserves current config.

## Paired product study protocol (M12a)

`evaluation schema` prints the plan/observation JSON schemas. `evaluation plan <plan.json>`
validates label evidence and prints SHA-256 of canonical validated plan JSON (UTF-8, sorted keys,
compact separators, model defaults included). `evaluation report <plan.json> <observations.json>`
requires that digest and verifies all referenced evidence. No initialized state, MCP extension,
runner configuration or migration is needed. JSON inputs are each bounded to 16 MiB.

Plans fix fixture/pilot kind, selection method, timezone-aware registration time, question,
baseline/treatment descriptions, configured baseline checks, success criteria, participants and
reviewed cases. Case source_revision is a Git commit or retained content fingerprint; both arms
must start from that exact source, with final sources/repairs retained in observation evidence.
The comparison unit is a planned case/participant pair, not an independent repository observation.
At most 5000 pairs; duplicate repository/revision/change-family cases are rejected.

Observations record one baseline and one DecisionGuard arm per pair, with completed/not_run/
unsupported/error status. Both arms must complete every planned baseline check (passed or failed)
to enter paired metrics. Missing observations and other statuses have explicit exclusion reasons.
A partial baseline can yield descriptive metrics but full_baseline_planned is false. Completed
observations require evidence; unknown outcomes stay unknown. Outcomes from unfinished runs are
rejected. Timing is finite nonnegative seconds; detection is timed from change availability.
Detection deltas use only pairs where both arms detected; missing times never become zero.

An escaped defect requires an observed defective integration, not merely a missed warning.
Non-integration is counted separately. Benign blocks use reviewer-labelled benign cases and known
block outcomes; they do not prove the gate's policy was wrong. Each rate exposes its denominator.
Setup failures retain spent time; feedback has yes/no/undecided/withdrew and missing counts.
Retries do not create new observations. Correct a record explicitly and retain the original in
the study archive; there is no append-only or tamper-proof observation database.

Evidence paths resolve beneath their containing plan or observations directory, never traverse
parents or reference external absolute/drive paths. SHA-256 is checked once per resolved file;
limits are 2048 unique files, 4 MiB per file, 64 MiB total. Files are read, never interpreted as
commands. Hashes establish consistency only; a trusted operator can rewrite a plan and its digest.
Report success criteria require manual review; effectiveness/release approvals and population
frequency inference are always false. The protocol is separate from Jev classification evaluation.

## Product alpha workflows

`setup project <request> [--apply]` consumes coordinator, reviewed RunnerConfig and explicit tasks
(task_id, actor, worktree, paths, optional contracts/integration). Default is filesystem/state-free
preview: validate repository identity/worktrees/paths and return a deterministic plan digest.
Apply uses ordinary initialization plus TaskRequest registration, with plan/task-derived retry keys.
Each step commits independently; retrying the original request resumes without duplicates. Existing
runner/coordinator configuration is preserved. No accepted decisions/assumptions or evidence are
generated. `next --task-id ... [--integration-task ...]` uses gate(record_receipt=False), orders all
original findings, executes no runner and persists no receipt. Exit 1 means blocked. Doctor now
checks every configured task override as well as default executable/cwd, and exits 1 on failure.

`reliability recovery/soak/filesystem-full` accept only new disposable destinations, never a live
database. Recovery kills actual review subprocesses, checks pre-commit rollback and post-commit
retry, exercises a SQLite page ceiling and backup restoration. Filesystem-full additionally
requires a POSIX filesystem of at most 16 MiB; it uses/reclaims a bounded filler file and verifies
subsequent mutations. Soak allows 2-4 workers, duration (0,28800] seconds and <=100000 seeded events.
Latency storage is capped at 100000 samples per worker; actual durations expose early termination.
Reports include percentile samples, state growth, contention counts and Python allocation peaks;
process RSS and production reliability remain unknown. Only a measured full duration can meet
the eight-hour duration flag. Quiescent final gates must pass for a successful short workload.

`evaluation kit <plan> <new-directory>` copies/re-hashes label evidence into portable paths, writes
a newly digest-bound plan, empty observations, schema and participant instructions. It collects no
feedback. Pilot feedback additionally requires consent_to_use=true. Optional pricing_interest
records not_asked/would_consider/would_not_pay/unknown; monthly_budget_minor and currency must be
supplied together and require would_consider. Reports label these as stated interest, never actual
payments. Fixture protocol tests do not establish customer willingness to pay.
