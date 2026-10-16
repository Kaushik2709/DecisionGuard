# MCP and Codex setup

Install DecisionGuard first (`uv sync --locked --group dev`) and initialize the target repository
using the CLI. Each server process uses one fixed `--actor`; register tasks using that same actor.
Use an ordinary agent identity for coding sessions. Coordinator identity is configured locally
at initialization; supplying a request role or spoofing another actor cannot grant capability.
These session restrictions apply to MCP. The CLI is a trusted local operator channel; agents
with unrestricted local shell access are outside this capability boundary.

MCP task registration creates an unapproved scope. The local coordinator must run
`approve-task-scope` before proposals or validation can use it. Authority configuration is
reloaded for mutations, so removing a coordinator also denies subsequent requests and cached
mutation retries on already-running sessions. Malformed configuration fails closed.
Before upgrading v1 state, stop all clients/servers, run `migrate --sessions-stopped`, approve
existing task scopes, and rerun validation. Keep the generated SQLite backup.

Example Codex configuration (replace absolute paths for your machine):

```toml
[mcp_servers.decisionguard]
command = 'D:\DecisionGuard\.venv\Scripts\python.exe'
args = ['-m', 'decisionguard.adapters.mcp', '--root', 'D:\YourRepository', '--actor', 'frontend']
```

Linux uses the environment's absolute `bin/python` path. Configure separate sessions with
their respective actor and repository/worktree root. Linked worktrees resolve the same state.
Do not point different actors at a single server whose bound actor differs.

The server uses the official Python SDK v1 stdio API, pinned below v2. stdout is reserved for
protocol messages; SDK diagnostics use stderr. `tests/transport/test_mcp.py` launches a real
SDK client, initializes the server, lists tools, checks structured results and forbidden inputs.
This is transport evidence; it does not establish that any particular interactive harness
automatically polls events or complies with a skill.

## Workflow skill

The distributable skill is `skills/decisionguard-workflow/SKILL.md`. Copy its containing folder
into the target repository's `.agents/skills/` for repository discovery, or the user's
`~/.agents/skills/`. It has the required `name` and `description` frontmatter and contains only
workflow instructions. The project does not change your global Codex configuration or install
the skill into another repository automatically.

Sources verified 2026-10-15:
[official skills discovery and frontmatter](https://learn.chatgpt.com/docs/build-skills),
[official MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[official SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x).
