# DecisionGuard adversarial audit

Date: 2026-10-15. Target: local working source, version 0.1.0, Windows / Python 3.12.8.
This workspace has no root Git repository, so no commit identifier is available.

## Remediation status

The seven findings below describe the **pre-hardening implementation**. They have now been
addressed in source, and `tests/security_audit/` contains rejection/recovery regressions rather
than assertions that unsafe behavior succeeds. The broader production risks remain threat-model
limits or operational follow-ups; this is not certification against hostile same-user agents.

| Finding | Implemented control |
|---|---|
| DG-01 | Changed paths outside approved task scope block the gate |
| DG-02 | Distinct integration task and worktree required; self-integration rejected |
| DG-03 | Task generation invalidates in-flight evidence |
| DG-04 | Authority reloaded for mutations and cached retries; live MCP revocation tested |
| DG-05 | Only latest reserved validation sequence eligible; receipts name exact runs |
| DG-06 | MCP scopes await coordinator approval; bounded task/proposal quotas |
| DG-07 | OS-backed setup lock, persistent identity journal, atomic config publication |

Database v2 adds explicit backed-up migration. Legacy scopes need approval and evidence must
be regenerated. Snapshots stream file bytes with configurable limits; the gate captures source
outside the writer transaction and checks a mutation epoch before committing. Receipt pruning
is explicit and preserves decision/run/retry history. The CI guide and demo now distinguish
single-candidate readiness from separate combined-source verification.

Completion review on 2026-10-16 additionally bounded file-name enumeration before materializing
the source list: configurable 16 MiB path-name budget, producer termination on count/time/byte
excess, incremental non-Git traversal, and pruned state/exclusion directories. Empty directory
trees and stalled Git producers have regression coverage. Changed-path scans use the same
budgets. Pruning emits success only after its transaction commits.

Cross-platform execution also found and fixed platform-dependent typing and exception
serialization through multiprocessing. CI actions are pinned to verified official commit
hashes and CI now runs the locked dependency audit. See `tasks.md` for final verification.

Final completion verification on 2026-10-16: **79 tests passed in each of Windows/Linux Python
3.11/3.12**, including rejection/recovery expectations for the seven original findings.
Lint, typing, demo, benchmark, package builds, refreshed dependency audit and actionlint passed.
Remote GitHub Actions and interactive multi-agent harness compliance remain unverified.

## Historical verdict before remediation

**Do not treat a passing gate as a production release authorization yet.** The normal
demo/benchmark exercise useful happy paths but do not cover the bypasses below.
The audit reproduced seven adverse behaviors, including two high-priority evidence
integrity problems. These are local workflow/application findings; this is not evidence
of an internet-accessible exploit. Production code has not been changed by this audit.

Severity is qualitative and relative to using DecisionGuard as a release gate. There
is no CVSS score, external penetration test, or claim that every vulnerability was found.

## System decomposition and actual capabilities

```text
Trusted local operator CLI              Agent client
           |                                |
           |                       fixed-actor stdio MCP
           +------------+-------------------+
                        |
              application services
              /         |          \
      typed domain   SQLite state   Git worktree identity
                        |
        local validation + source snapshots
                        |
             gate findings / receipts
```

| Part | Implemented capability | Security boundary / limitation |
|---|---|---|
| Domain | Typed contracts, categorical compatibility, unknown schema/text comparisons | Compares declarations; does not infer actual program behavior |
| Lifecycle services | Register tasks, assumptions, proposals, coordinator review, refresh, mappings | Authority is local configuration and fixed MCP actor; CLI is trusted |
| Storage | SQLite WAL, transactions, optimistic predecessors, idempotency, events | Same-user writable state; no independent tamper-resistant authority |
| Git | Common-directory identity and linked worktree checks | Not a sandbox; external environment and ignored inputs remain outside evidence |
| Validation | Configured argv, timeout, bounded retained output, pre/post source hashes | Executes project code with the operator's OS privileges |
| Gate | Conflicts, coverage, pending changes, evidence freshness, combined-source comparison | Confirmed false-clear paths below |
| CLI | Init, status/context, task/assumption/proposal/review/mapping, events/ack, refresh/conflicts, validate/gate, import/export, demo/benchmark | Actor names are operator assertions, not credentials |
| MCP | Ten tools for coordination and gate checks; fixed session actor | No validation-command tool; sessions retain startup configuration |
| Portability | Typed accepted history/mapping export and import, local identity rebinding | Coordinator must trust/review metadata; imported passing runs are disallowed |
| AI integration | Workflow skill and tool interface usable by coding agents | No LLM, semantic extraction, model evaluation, agent sandbox, or orchestration engine |
| Evaluation | Deterministic demo and 14-case planted classifier benchmark | Does not establish live-agent reliability or adversarial security |

There is no web application, network listener in the supplied stdio entry point, cloud
service, user-account system, or automatic merge operation. HTTP-specific SDK advisories
must not automatically be described as reachable vulnerabilities in this application.

## Database assessment

Git state lives at `<git-common-dir>/decisionguard/state.db` with adjacent `config.json`.
Non-Git state is explicitly selected. Linked worktrees share the same database.

| Table | Responsibility | Integrity properties |
|---|---|---|
| `meta` | Project UUID and revision | Application maintains values |
| `versions` | Immutable contract history, JSON bodies | Composite primary key; update/delete abort triggers |
| `heads` | Active version per contract | Composite foreign key to `versions` |
| `entities` | Tasks, proposals, assumptions, runs, mappings, resolutions, receipts, imports | Generic `(kind,id,body)` store; most relationships are application-enforced |
| `events` | Monotonic task notifications | Autoincrement ID; no task foreign key |
| `cursors` | Delivered and acknowledged event positions | No task foreign key or SQL constraint tying positions to events |
| `retries` | Actor/key request fingerprint and saved response | Composite key provides transactional idempotency |

Strengths: SQL values are parameterized in the reviewed code; writes use `BEGIN IMMEDIATE`;
busy handling is bounded; foreign keys are enabled on each connection; history publication,
revision changes, notifications and retry results share a transaction.

Gaps: JSON bodies lack database-level schema checks, many logical references have no foreign
keys, there is no retention/quota policy, and receipts/events are not cryptographically
attested. Filesystem access can bypass application authority. The immutability triggers do
not protect against an OS user who can replace the database or alter its schema. This last
point is explicitly outside the documented same-user threat model, not a newly discovered
authorization bypass. SQLite runtime observed: 3.45.3; the dependency audit below does not
certify the bundled SQLite runtime or Python interpreter.

## Confirmed findings

### DG-01 — High: changed code can be absent from a passing combined integration

Source: `src/decisionguard/application/validation.py`, coverage loop and `expected_files` /
`combined_files` comparison (around lines 149–228).

Precondition: a selected task declares narrow `paths`, while its accepted dependency has
broader scope. No direct database editing or coordinator impersonation is required.

Reproduction: register a task for `check.py` under an existing contract covering both
`check.py` and `code.py`. Change `code.py` from amount `499.00` to `999.00`. Leave the
integration worktree at `499.00`. Run valid commands in both worktrees. The gate returns
`passed: true` and `integration_checked: true` despite the different application code.

Cause: coverage accepts changed files covered by a dependency, but combined comparison
only compares `task.paths`. Those sets are not required to agree.

Fix: require every changed file to be in declared task scope, or compare the union of
declared scope and actual task changes against the combined tree. Preserve deletions and
reject unsupported source types. Regression acceptance: this exact missing-code case blocks.

### DG-02 — Medium: integration evidence can compare a task with itself

Source: `application/services.py:register` and `application/validation.py:gate`.

Reproduction: register selected and integration tasks on the same linked worktree. Both
validate and the integration gate passes. Also, `gate([integration], integration)` passes,
reusing the same task and evidence for both roles.

Cause: integration registration checks separation only from the configured original root;
the gate does not require separation from the selected implementation worktrees/tasks.

Impact: `integration_checked` can imply independent combined verification when none occurred.
Fix: reject an integration task present in the selected set and require its resolved worktree
identity to differ from every selected worktree. Verify selected revisions in a genuine merge
candidate. Do not claim that merely creating another task creates isolation.

### DG-03 — Medium: an in-flight run can restore evidence invalidated by refresh

Source: `application/services.py:invalidate` and `application/validation.py:validate`.

Reproduction: pause validation after the real configured command returns, call refresh from
a second execution context, then allow finalization. The run becomes valid and the gate passes.
The probe uses events to control ordering, not a probabilistic sleep.

Cause: invalidation only changes runs already marked valid. An executing run is initially
invalid. Finalization checks dependency values/revision, but refresh need not change either.
There is no task evidence-generation counter to detect the intervening invalidation.

Impact: the promised fresh-validation-after-refresh ordering is not enforced. This probe
does not demonstrate changed source or changed decision versions slipping past their checks.
Fix: increment a task generation on every evidence-invalidating mutation; capture it at
reservation and compare it transactionally at finalization and gate time.

### DG-04 — Medium: coordinator removal does not revoke an existing MCP session

Source: `application/services.py:43–58`.

Reproduction: create a coordinator-bound service, replace the configured coordinator with
another identity, and accept a proposal through the old service. Acceptance still succeeds.
A new service sees the updated coordinator list.

Cause: authorization uses `self.config` loaded once during construction. The MCP server
holds this service for its lifetime.

Impact: local permission revocation requires terminating/restarting every old session.
Startup-bound configuration is described in the architecture, but there is no revocation
mechanism or explicit operational revocation procedure. This is a production control gap,
not the ability of an ordinary worker to invent coordinator rights.

Fix: reload authority safely per mutation or use a configuration generation that invalidates
old sessions. Document restart-only revocation if retained. Test rejection on an already-open
session after removal, including idempotent retry policy.

### DG-05 — High: a newer failed validation can be hidden by an older success

Source: `application/validation.py:173–190`.

Reproduction: run the configured command successfully. Change a disposable external
sentinel consumed by that same command and run it again: exit code 1. With identical tracked
source/configuration/decisions, the gate still returns `passed: true` using the older run.
The sentinel models an external service or environment dependency deterministically.

Cause: gate selects any matching historical passing run. A failed newer run does not
invalidate earlier successes or act as a barrier.

Impact: known current negative evidence is ignored. Although environment-only changes are
outside source hashing by design, this finding is about ignoring a failure already recorded
by DecisionGuard itself.

Fix: require the latest applicable validation attempt to finish successfully and freshly;
define ordering using a durable task run sequence. A newer failed/error/interrupted attempt
must not be silently superseded by an older success. Include overlapping-run tests.

### DG-06 — Medium: a worker can create repository-wide pending-impact blockage

Source: `application/services.py:propose` and `findings` (around lines 184–209 and 480–497).

Reproduction: a fixed-actor ordinary worker with a task scoped to `check.py` proposes a new,
unrelated contract with scope `.`. Another task becomes blocked by `pending_impact`, without
coordinator approval. Rejection clears it; the worker can submit another fresh proposal.

Cause: proposal scope is checked for path safety but not limited to authorized task scope.
There are no proposal quotas, rate limits or broader-scope approval workflow.

Impact: a buggy or malicious agent can repeatedly disrupt all repository gates. Blocking
relevant pending proposals is an intentional safeguard; unrestricted scope and unbounded
submission make it an availability risk when workers are not fully cooperative.

Fix: distinguish proposed impact from authorized scope; require coordinator promotion for
out-of-scope proposals, and add actor/task budgets and auditable dismissal controls. Preserve
legitimate cross-cutting changes through an explicit approval path.

### DG-07 — Medium: failed initialization leaves state that normal retry cannot recover

Source: `application/config.py:initialize` and `storage/sqlite.py:Store.__init__`.

Reproduction: inject an I/O failure opening `config.json` after the database is created.
The database remains, config is absent, and retrying initialization fails with
`Foreign project database` because it generates a new project UUID.

Impact: crash/disk failure during setup requires manual recovery. No data loss was exercised.
Fix: use a recoverable initialization protocol with a persistent initialization identity,
atomic config publication and an exclusive setup lock. Never solve this by deleting an
existing state database automatically. Test failures at each persistence boundary.

## Additional production risks from inspection

These were not subjected to destructive load or hostile OS-level testing:

- **Resource exhaustion:** snapshot hashing reads each entire file into memory, scans the
  tree repeatedly, and repeats capture inside the SQLite write transaction. Large source
  trees can hold the single writer for a long time. Entity queries load all bodies, and
  each gate adds another receipt. Add streaming hashes, work budgets, retention, bounded
  queries and a design that minimizes filesystem work under the database writer lock.
- **Runner isolation:** configured argv prevents MCP command injection, but tests remain
  arbitrary executable code with inherited OS access/environment. Timeout/output bounds
  are not CPU/memory/network/filesystem isolation. Process-tree cleanup of detached children
  and Windows Job Object containment were not verified. Use an isolated worker if code is
  untrusted, and keep secrets out of its environment and retained output.
- **Incomplete evidence universe:** ignored/untracked inputs, installed dependencies,
  interpreter binaries, environment variables and external services are not fully bound
  into evidence. Pre/post snapshots cannot detect edit-and-restore during execution.
  Existing architecture documentation acknowledges these limits.
- **AI-mediated trust:** agent-written rationale, values and evidence paths are untrusted
  content later read by a coordinator/model. No live prompt-injection trial was performed.
  Treat those fields as data; require deliberate human/policy review for authority changes.
- **Weak semantic guarantees:** a matching declaration, a broad contract scope and a weak
  test can pass despite incorrect business logic. No static semantic analyzer or live-agent
  evaluation exists. The benchmark's 100% score is only its planted cases.
- **Operational readiness:** no backup/restore exercise, disk-full/WAL recovery campaign,
  long-running soak, hostile multi-user deployment, or Linux security validation was done.
  Workflow actions use version tags rather than immutable commit pins; no dependency audit
  step is currently in CI.

## Evidence and reproduction

The original probes in `tests/security_audit/test_adversarial_audit.py` reproduced the unsafe
behavior described above. They have since been converted to fail-closed/recovery regressions:
passing now means the former bypass is rejected or the recovery succeeds. Historical results
below record the original audit, not the hardened suite.

```powershell
cd D:\DecisionGuard
.venv\Scripts\python.exe -m pytest tests/security_audit -v --basetemp artifacts/audit-repro-new
uv audit --frozen --cache-dir .cache-clean\uv
```

All reproduction writes use disposable pytest repositories/state. No production database,
global configuration, credentials, remote repository, or application source was modified.
The initialization failure and validation race use controlled fault injection. Other probes
use real service methods, SQLite, Git worktrees and configured subprocess execution. The
existing transport suite separately exercises real MCP stdio; every finding was not repeated
over that transport.

Executed verification:

- Existing 38 tests plus the first six audit probes: **44 passed in 99.90 seconds**.
- Final dedicated audit run, including the added initialization-failure probe:
  **7 passed in 18.21 seconds**. This confirms seven reproductions, not seven security fixes.
- Ruff check and formatting check passed; mypy passed for 24 source files.
- JUnit evidence: `artifacts/security-audit-results.xml` and
  `artifacts/security-audit-probes.xml` (generated, ignored files).

Dependency check: `uv audit --frozen --cache-dir .cache-clean\uv` queried OSV successfully
and reported **no known vulnerabilities or adverse project statuses in 48 packages**.
The initial sandbox attempt could not connect; the approved network retry succeeded.
This is a point-in-time known-advisory check, not proof of vulnerability absence.
Tool semantics: [official uv audit documentation](https://docs.astral.sh/uv/reference/cli/#uv-audit).

## Original remediation order (implementation now delivered)

1. Fix DG-01 and DG-05 before relying on gates for releases.
2. Enforce DG-02 isolation and DG-03 generation-based invalidation.
3. Resolve DG-04 revocation, DG-06 scope/budget policy, and DG-07 setup recovery.
4. Add database recovery tests, bounded resource usage, isolated execution and CI advisory checks
   according to the intended deployment threat model.
5. Rerun each adversarial case with rejection expectations, the ordinary suite, Windows/Linux
   CI, and a real multi-agent workflow. Only then reassess production readiness.
