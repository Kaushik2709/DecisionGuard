import asyncio
import json
import sys
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_stdio_client_and_bound_actor(project):
    service, root = project

    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "decisionguard.adapters.mcp", "--root", str(root), "--actor", "worker"],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=15)
            ) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert names == {
                    "get_context",
                    "register_task",
                    "declare_assumption",
                    "propose_decision",
                    "review_proposal",
                    "poll_events",
                    "acknowledge_event",
                    "refresh_dependencies",
                    "list_conflicts",
                    "check_gate",
                    "preview_contracts",
                    "explain_impact",
                    "list_advisories",
                }
                response = await session.call_tool("get_context", {"task_id": "worker"})
                assert not response.isError
                context = json.loads(response.content[0].text)
                assert context["schema_version"] == 1
                denied = await session.call_tool(
                    "refresh_dependencies",
                    {
                        "request": {
                            "actor": "coordinator",
                            "task_id": "worker",
                            "idempotency_key": "spoof",
                        }
                    },
                )
                assert denied.isError
                assert json.loads(denied.content[0].text)["error"]["code"] == "FORBIDDEN"
                invalid = await session.call_tool(
                    "register_task",
                    {
                        "request": {
                            "actor": "worker",
                            "task_id": "bad",
                            "idempotency_key": "bad",
                            "worktree": str(root),
                            "paths": ["code.py"],
                            "command": "arbitrary",
                        }
                    },
                )
                assert invalid.isError
                result = await session.call_tool("check_gate", {"task_ids": ["worker"]})
                assert not json.loads(result.content[0].text)["receipt"]["passed"]

    asyncio.run(exercise())
