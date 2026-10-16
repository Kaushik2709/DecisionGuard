import asyncio
import json
import sys
from datetime import timedelta

from conftest import key, proposal
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_running_mcp_session_rejects_revoked_coordinator_and_cached_retry(project):
    service, root = project
    pending = proposal(service)["proposal"]

    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "decisionguard.adapters.mcp",
                "--root",
                str(root),
                "--actor",
                "coordinator",
            ],
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=20)
            ) as session:
                await session.initialize()
                request = {
                    "actor": "coordinator",
                    "proposal_id": pending["proposal_id"],
                    "accept": False,
                    "expected_version": 1,
                    "rationale": "Live review",
                    "idempotency_key": key(),
                }
                result = await session.call_tool("review_proposal", {"request": request})
                assert not result.isError
                config = service.config.model_copy(update={"coordinators": ["replacement"]})
                (service.directory / "config.json").write_text(config.model_dump_json())
                retry = await session.call_tool("review_proposal", {"request": request})
                assert retry.isError
                assert json.loads(retry.content[0].text)["error"]["code"] == "FORBIDDEN"
                request["idempotency_key"] = key()
                fresh = await session.call_tool("review_proposal", {"request": request})
                assert fresh.isError

    asyncio.run(exercise())
