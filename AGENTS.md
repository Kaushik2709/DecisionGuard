# DecisionGuard — Coding Agent Instructions

Read `rules.md`, `PRD.md`, and `architecture.md` first. Read `design.md` before
changing models, storage, or adapters. Use `tasks.md` for milestones and verification.
Maintain the resumable checkpoint in `memory.md` after each milestone.

Preserve unrelated user work. Work sequentially unless the user authorizes parallel
agents. Build a runnable vertical slice before expanding. Domain logic stays independent
of storage and adapters; CLI and MCP share application services.

Use a shared database per repository, transactions, optimistic versions, and idempotency.
Published decision versions are immutable. Accepted changes invalidate evidence atomically.
Never silently accept proposals or resolve disagreements. Acknowledgement is not validation.
Bind evidence to source and decision versions; report unknown coverage honestly.

Never execute MCP-supplied commands. Verify official SDK and harness documentation before
integration. Do not invent hooks or configuration fields. The core requires no LLM or API key.
Test real concurrency, linked worktrees, retries, persistence, source freshness, transport,
and combined integration. Never fabricate test results or benchmark scores.
