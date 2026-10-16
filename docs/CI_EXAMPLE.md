# Portable metadata and integration in CI

1. Locally export reviewed metadata: `decisionguard export reviewed-contracts.json`.
2. Review and commit that JSON intentionally. It contains no local commands, authority,
   tasks, validation passes, or gate receipts. Use repository-relative evidence locations.
3. CI checks out the intended combined candidate source and creates a separate linked worktree
   using `git worktree add --detach <integration-path> HEAD`.
4. Initialize CI-local state with a reviewed runner JSON and coordinator actor, then import
   the reviewed metadata using `decisionguard import review-request.json reviewed-contracts.json`.
5. Register an integration task at that linked worktree, select dependency contracts, declare
   current assumptions, and run `validate` through the CLI.
6. For a single prepared CI candidate, run `gate --task-id integration`; fail CI on exit 1 or 2.
   This validates candidate readiness and returns `integration_checked: false`. Do not label
   this as independent integration verification. For combined verification, register and
   validate the selected implementation tasks in distinct worktrees, then run
   `gate --task-id frontend --task-id backend --integration-task integration`.
   The integration task must differ from every selected task and worktree.

Request JSON files and runner configuration should live outside captured source (for example
in the shared state directory) so administrative artifacts do not become unknown changed paths.
Imports always require fresh local validation. Exported history is user-reviewed metadata,
not a signed trust artifact. The CI checkout/merge policy supplies the candidate combination;
DecisionGuard never performs a merge and cannot make future merge/state updates atomic.

The project's own `.github/workflows/ci.yml` runs Windows/Linux verification, the executable
demo, and the benchmark. Remote workflow results remain unverified until CI actually runs.
