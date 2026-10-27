import argparse
import functools
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any, ParamSpec

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

from decisionguard.application.config import state_dir
from decisionguard.application.services import Service, envelope
from decisionguard.application.validation import gate
from decisionguard.domain.contracts import ContractScan
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AckRequest,
    AssumeRequest,
    ProposeRequest,
    ReviewRequest,
    TaskMutation,
    TaskRequest,
)
from decisionguard.storage.sqlite import dumps

P = ParamSpec("P")


def guarded(function: Callable[P, dict[str, Any]]) -> Callable[P, dict[str, Any] | CallToolResult]:
    @functools.wraps(function)
    def invoke(*args: P.args, **kwargs: P.kwargs) -> dict[str, Any] | CallToolResult:
        try:
            return function(*args, **kwargs)
        except (GuardError, OSError, ValueError, sqlite3.Error) as exc:
            code = exc.code if isinstance(exc, GuardError) else "OPERATIONAL"
            message = exc.message if isinstance(exc, GuardError) else "Local operation failed"
            error = envelope(error={"code": code, "message": message})
            return CallToolResult(
                isError=True,
                structuredContent=error,
                content=[TextContent(type="text", text=dumps(error))],
            )

    return invoke


def build_server(service: Service) -> FastMCP:
    server = FastMCP("DecisionGuard")

    @server.tool()
    @guarded
    def get_context(task_id: str | None = None) -> dict[str, Any]:
        """Retrieve accepted decisions before implementation or after a change."""
        return service.context(task_id)

    @server.tool()
    @guarded
    def register_task(request: TaskRequest) -> dict[str, Any]:
        """Register a task in a linked worktree with explicit dependencies."""
        return service.register(request)

    @server.tool()
    @guarded
    def declare_assumption(request: AssumeRequest) -> dict[str, Any]:
        """Declare expected implementation behavior at an accepted version."""
        return service.assume(request)

    @server.tool()
    @guarded
    def propose_decision(request: ProposeRequest) -> dict[str, Any]:
        """Propose a versioned contract change without changing accepted state."""
        return service.propose(request)

    @server.tool()
    @guarded
    def review_proposal(request: ReviewRequest) -> dict[str, Any]:
        """Explicit review; requires server-configured coordinator authority."""
        return service.review(request)

    @server.tool()
    @guarded
    def poll_events(task_id: str, actor: str, after: int = 0, limit: int = 100) -> dict[str, Any]:
        """Poll durable task events at implementation checkpoints."""
        return service.poll(task_id, actor, after, limit)

    @server.tool()
    @guarded
    def acknowledge_event(request: AckRequest) -> dict[str, Any]:
        """Acknowledge delivery; never creates validation evidence."""
        return service.ack(request)

    @server.tool()
    @guarded
    def refresh_dependencies(request: TaskMutation) -> dict[str, Any]:
        """Refresh knowledge after revisiting code; does not validate implementation."""
        return service.refresh(request)

    @server.tool()
    @guarded
    def list_conflicts(task_ids: list[str] | None = None) -> dict[str, Any]:
        """Explain conflicts, pending impacts, and stale declared knowledge."""
        return service.conflicts(task_ids)

    @server.tool()
    @guarded
    def check_gate(task_ids: list[str], integration_task: str | None = None) -> dict[str, Any]:
        """Check fresh runner evidence and actual combined source; executes no commands."""
        return gate(service, task_ids, integration_task)

    @server.tool()
    @guarded
    def preview_contracts(request: ContractScan) -> dict[str, Any]:
        """Preview approved-scope local OpenAPI files. No publication or network requests."""
        from decisionguard.application.contracts import scan

        return scan(service, request)

    @server.tool()
    @guarded
    def explain_impact(task_ids: list[str] | None = None) -> dict[str, Any]:
        """Explain current impacts and required revalidation; executes nothing."""
        return service.impact(task_ids)

    @server.tool()
    @guarded
    def list_advisories(task_id: str, limit: int = 100) -> dict[str, Any]:
        """Read probabilistic advisory history. Cannot submit code or alter clearance."""
        from decisionguard.application.advisories import list_advisories as read

        return read(service, task_id, limit)

    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--state", type=Path)
    parser.add_argument("--actor", required=True, help="Fixed identity for this server process")
    args = parser.parse_args()
    try:
        service = Service(state_dir(args.root.resolve(), args.state), session_actor=args.actor)
        build_server(service).run(transport="stdio")
    except GuardError as exc:
        import json
        import sys

        print(
            json.dumps(envelope(error={"code": exc.code, "message": exc.message})), file=sys.stderr
        )
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
