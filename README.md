# DecisionGuard

Local-first decision consistency for agents working in Git worktrees. Python 3.11+.

DecisionGuard tracks shared contracts, affected tasks, and validation tied to current source.
It provides a CLI, official MCP stdio server, shared SQLite state across linked worktrees,
explicit coordinator review, durable polling, and scoped integration gates. No API key is needed.

It coordinates reviewed agreements and fresh validation across parallel worktrees. Existing
schemas/codegen and contract/integration tests remain the baseline. The offline
[paired product study](docs/PRODUCT_EVALUATION.md) measures incremental value, setup effort and
benign blocks without granting effectiveness or release approval. Real-user benefit is unverified.
The [alpha workflow](docs/ALPHA_WORKFLOW.md) adds guided setup, current-source next actions,
disposable recovery/soak checks and an empty pilot kit. The [strong baseline fixture](examples/strong-baseline/README.md)
runs actual schema/codegen/type/contract/HTTP checks and credits baseline detections.

The unreleased next phase adds reviewed OpenAPI 3.1.x contracts, directional schema checks,
impact/watch/doctor commands, backup/restore and optional previewed Jev advisories. Advice
never changes clearance. See the [TypeScript/Python example](examples/fullstack-checkout/README.md)
and [evaluation/release gates](docs/ADVISORY_EVALUATION.md). A portal and automatic agent-to-agent
delivery are not implemented. This remains a trusted local-user tool, not a hosted service.

Existing schema 1/2 installations must stop all clients before
`decisionguard migrate --sessions-stopped`. Migration backs up the database and invalidates prior validation. Never
migrate beside legacy clients; regenerate evidence afterward. Database schema is 3; CLI/MCP
envelopes remain version 1, and exported metadata is version 2 with v1 import support.

Useful new commands (use `--help` for positional arguments):

```
decisionguard --root <repository> doctor
decisionguard --root <repository> setup codex frontend
decisionguard --root <repository> impact
decisionguard --root <repository> watch frontend frontend --once
decisionguard --root <repository> backup <new-backup.db>
decisionguard --root <repository> maintain
```

`setup codex` prints a configuration preview; it does not install it or change global settings.
`maintain` previews pruning; `--apply` is explicit. Archival, restore and proposal operations use
structured JSON requests. Optional `uv sync --locked --extra jev --group dev` installs the Jev
extra. Only `advice classify` makes a model request using `DECISIONGUARD_JEV_API_KEY`; preview,
normal gates and offline tests do not. Never share uninspected source or put keys in JSON.

## Install and try

Requires Git, Python 3.11+, and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --locked --group dev
uv run decisionguard --help
uv run decisionguard demo
uv run decisionguard benchmark
```

The demo retains disposable repositories under `artifacts/`. It exposes a real 100× mismatch
after a clean merge, blocks acknowledgement-only completion, and passes after repaired source
and fresh combined checks. A second scenario rejects the change and preserves an explicit
conversion adapter. Agents are simulated; no model calls occur. See [the demo guide](examples/checkout/README.md).
If a managed Windows environment blocks the default uv cache, set `UV_CACHE_DIR` to a writable
local directory before syncing. Keep caches outside captured application source.

## Initialize a repository

Create a reviewed runner JSON **outside the target source tree**, using the absolute Python
path for the target project's environment:

```json
{"argv":["D:/YourRepository/.venv/Scripts/python.exe","-m","pytest","-q"],"cwd":".","timeout":120,"output_limit":16000}
```

From this installed checkout:

```powershell
uv run decisionguard --root D:/YourRepository init coordinator D:/scratch/runner.json
uv run decisionguard --root D:/YourRepository status
```

State/config live in `decisionguard/` beneath the canonical Git common directory. Linked
worktrees share state automatically; independent clones do not. For non-Git projects supply
both `--root` and `--state`. Isolated integration requires Git. SQLite must stay on a local
filesystem supporting WAL. Never commit mutable state.

## CLI workflow

Structured mutations take a JSON request file. Keep requests outside captured source or in
the shared state directory. Every mutation requires actor and idempotency key. Identical retries
return the recorded result; changed payloads using the same key fail.

Register an author task before proposing the first contract (`task request.json`):

```json
{"actor":"backend","task_id":"backend","idempotency_key":"register-backend-1","worktree":"D:/YourRepository","paths":["src/checkout.py","tests/test_checkout.py"],"contracts":[]}
```

Propose (`propose request.json`):

```json
{"actor":"backend","task_id":"backend","idempotency_key":"public-contract-1","contract":{"boundary":"checkout.public.request","key":"amount.unit"},"value":{"kind":"money_unit","value":"INR.major.decimal-string"},"expected_version":0,"scope":["src/checkout.py","tests/test_checkout.py"],"rationale":"Public clients send decimal major units"}
```

Copy the returned proposal ID into a coordinator review (`review request.json`):

```json
{"actor":"coordinator","idempotency_key":"review-public-1","proposal_id":"REPLACE_WITH_RETURNED_ID","accept":true,"expected_version":0,"rationale":"Reviewed public boundary"}
```

Declare the implementation assumption (`assume request.json`):

```json
{"actor":"backend","task_id":"backend","idempotency_key":"assume-public-1","contract":{"boundary":"checkout.public.request","key":"amount.unit"},"expected":{"kind":"money_unit","value":"INR.major.decimal-string"},"observed_version":1,"evidence":["src/checkout.py"]}
```

Later tasks can register with `contracts` containing accepted `{boundary,key}` identities.
Poll with `events backend backend --after 0 --limit 100`, then use the returned delivery cursor.
`ack` takes actor/key/task_id/event_id JSON. `refresh` takes actor/key/task_id JSON, updates observed
versions, and retains expected values; changed expectations require another `assume` request.

Run `validate request.json` with:

```json
{"actor":"backend","task_id":"backend","idempotency_key":"validation-1"}
```

Validation commands come only from reviewed local config. Optional `task_runners` maps task
IDs to runner objects; `runner` is the default. Configuration changes require fresh validation
and invalidate prior evidence. Authority changes apply to subsequent mutations without a
server restart. Interrupted runs are unusable: inspect them and use a new key rather than
expecting an identical retry to rerun a command.

Prepare combined source yourself in a separate linked worktree, register an integration task
with `integration: true` and all selected dependencies, declare assumptions, and validate it:

```powershell
uv run decisionguard --root D:/YourRepository gate --task-id frontend --task-id backend --integration-task integration
```

A single-task gate without integration checks task readiness only. Multiple tasks require an
integration task. The gate compares selected implementation files against the combined snapshot.
Changed-path coverage includes commits made since each task was registered.
Exit codes: 0 passes the declared scope, 1 blocked/failed/stale/unknown, 2 operational/invocation
error. Recheck after any changes; a receipt does not make a future merge atomic.

Only the latest validation attempt can pass the gate. A later failure, error, timeout or
unfinished attempt blocks earlier success. Changed files must fit approved task scope, and
integration must use a distinct task and worktree. See [the audit](docs/SECURITY_AUDIT.md).

## Upgrading and scope approval

Stop all running DecisionGuard CLI/MCP sessions before upgrading database v1 or v2:

```powershell
uv run decisionguard --root D:/YourRepository migrate --sessions-stopped
```

The migration keeps a SQLite backup, preserves history and invalidates old evidence. A v1
migration also requires approval of existing scopes; v2 retains its approved scopes.
Fresh CLI registrations are locally approved; MCP registrations
need explicit coordinator approval. Supply this JSON to `approve-task-scope request.json`:

```json
{"actor":"coordinator","task_id":"backend","idempotency_key":"scope-backend-1","expected_scope_revision":0,"paths":["src/checkout.py","tests/test_checkout.py"]}
```

Approval changes require fresh validation. Broad contract proposals need approved broad scope;
use an explicitly approved proposal task when the change spans multiple implementation tasks.
Configuration supports optional resource `limits` described in [design.md](design.md).
Path enumeration is bounded before hashing, including a 16 MiB default `snapshot_name_bytes`
budget. Adding this limit changes the configuration digest: regenerate validation evidence
after updating an existing installation. All v1/v2 installations must migrate to schema 3.
`prune-receipts --days 30 --keep 1000` is explicit maintenance and preserves decision/run/retry
history. Initialization retries recover its journaled identity; never delete a database to
resolve a setup error without inspecting and backing up its contents.

Other commands: `context`, `conflicts`, coordinator `mapping`, `export`, coordinator `import`.
Each command has `--help`; [design.md](design.md) defines protocol and failure semantics.

## MCP, skill, and CI

See [MCP setup](docs/MCP_SETUP.md) for fixed-actor configuration and the distributable Codex
skill, and [CI example](docs/CI_EXAMPLE.md) for reviewed metadata transfer requiring fresh
validation. The workflow skill follows [official discovery rules](https://learn.chatgpt.com/docs/build-skills).

## Verification and limitations

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Tests include real multiprocess contention, worktrees with spaces, source/config/decision drift,
restart/idempotency, actual combined-source checks, import freshness, and a real MCP client.
See [memory.md](memory.md) for actual commands/results. Windows/Linux CI is configured;
remote results require an actual CI run.

Coverage and assumptions are declared. Arbitrary code behavior and architectural prose are
not inferred. Gitignored untracked files and reviewed exclusions are outside default snapshots.
Pre/post digests cannot detect malicious edit-and-restore. Revision changes conservatively
require fresh validation even for unrelated contracts. State trusts the same local user, who
can edit config/database directly. Skills cannot guarantee polling compliance. Gates do not
prove whole-repository correctness. The planted benchmark is diagnostic evidence.
Optional AI extraction remains deferred.

## License

DecisionGuard is available under the [MIT License](LICENSE), with the notice
`Copyright (c) 2026 Kaushik Mukherjee`. Dependency licenses remain their own;
this project license does not replace their attribution or redistribution conditions.

Read [PRD.md](PRD.md), [architecture.md](architecture.md), [design.md](design.md),
[rules.md](rules.md), [tasks.md](tasks.md), and [memory.md](memory.md).

Official references: [MCP SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x),
[Pydantic models](https://docs.pydantic.dev/latest/concepts/models/),
[Typer](https://typer.tiangolo.com/tutorial/), [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/).
