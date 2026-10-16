# Engineering rules

- Preserve unrelated work; develop sequentially unless parallel agents are explicitly authorized.
- Keep domain independent from adapters/storage; share application services across CLI and MCP.
- Use validated project/task identity, transactions, expected versions, and idempotency on mutations.
- Never edit published versions or silently select winners. Acceptance invalidates evidence atomically.
- Treat acknowledgement, refresh, attestations, and verified implementation as distinct states.
- Fail strict gates on unknown compatibility or unknown declared coverage. Explain every finding.
- Never run MCP-supplied commands. Use configured argv, explicit cwd, timeouts, bounded output,
  no shell interpolation, and source/config/decision freshness checks.
- Validate paths, reject traversal/foreign worktrees, avoid logging secrets.
- Verify official APIs; use a lockfile. No mandatory LLM, paid API, cloud, or dashboard.
- Use Python 3.11+, Ruff formatting/lint, mypy strict, pytest behavior tests, Windows/Linux CI.
- Verify real multiprocess writes, persistence, linked worktrees, and MCP subprocess transport.
- Record actual commands/results and limitations. Never claim fixture tests are live-agent evaluations.
- Keep canonical docs concise; update tasks and memory after milestones. Personal memories are untouched.
- Gate only the latest reserved validation sequence at the current task generation. Never fall
  back to historical success after a newer failure. No self-integration or unapproved task scope.
- Run source capture outside writer transactions; recheck the database epoch before receipt commit.
- Preserve existing databases during recovery; migrate only with stopped sessions and a backup.
