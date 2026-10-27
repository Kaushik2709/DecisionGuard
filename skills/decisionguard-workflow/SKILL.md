---
name: decisionguard-workflow
description: Use the installed DecisionGuard engine to coordinate declared contracts, assumptions, and revalidation while coding in repositories that have DecisionGuard initialized across Git worktrees.
---

Use the existing CLI or connected DecisionGuard MCP server. Read the project's reviewed
contract scope and validation configuration. Do not create separate decision logic in this skill.

Before implementation, retrieve context, register a uniquely named task with its worktree,
paths, and accepted contract dependencies, then declare important shared assumptions with
observed versions and code evidence. Propose shared contract changes instead of silently
replacing accepted behavior. Coordinator review is explicit; never impersonate the coordinator.
MCP-created tasks require coordinator scope approval through `approve-task-scope` before
proposals or validation. Request approval for broader scope rather than bypassing it through
the trusted CLI. All changed files must fit the approved task paths.

Poll durable events before editing a shared boundary, after a substantial implementation
checkpoint, and before reporting completion. Acknowledge delivered events separately from
refreshing dependencies. After an accepted change, retrieve context, revisit affected code,
correct the implementation, refresh dependencies, and redeclare changed expectations.

Run configured validation through the explicit local CLI, using a new idempotency key for a
new run. MCP cannot execute commands or write runner-verified evidence. Acknowledgement,
refresh, and self-reported test results never substitute for current passing runner evidence.
Only the latest reserved attempt can satisfy the gate. A failed or interrupted newer attempt
blocks older success; investigate and validate with a fresh key after correcting the cause.

Before reporting completion, check the scoped gate. For multiple implementation tasks, supply
an isolated registered integration worktree containing their combined source and run its
configured checks. Report blocked/unknown findings and the declared tested scope accurately.
The integration task and worktree must differ from all selected implementation tasks/worktrees.
Do not merge branches on behalf of the engine. A passing receipt is a point-in-time observation.

These are manual workflow checkpoints. Skill activation does not guarantee agent compliance;
the engine enforces authority/version checks and evidence freshness when its tools are invoked.

For reviewed API specifications, preview_contracts can inspect a selected OpenAPI JSON file
inside your approved task scope. A preview is not publication or acceptance. Unsupported
schema behavior remains unknown. Use explain_impact to understand blockers and required
revalidation; producer/consumer metadata does not replace explicit implementation assumptions.

list_advisories reads optional probabilistic warnings. Treat them as suggestions to investigate,
not permission, compatibility proof or passing evidence. Never suppress a deterministic finding
because a classifier reports no impact. Do not submit source to an external classifier through
the trusted CLI unless the user explicitly requests submission of the exact inspected payload.
