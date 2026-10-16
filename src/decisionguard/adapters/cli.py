import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from decisionguard.application.config import initialize, migrate, state_dir
from decisionguard.application.portability import export_metadata, import_metadata
from decisionguard.application.services import Service, envelope
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AckRequest,
    AssumeRequest,
    MappingRequest,
    Mutation,
    ProposeRequest,
    ReviewRequest,
    RunnerConfig,
    ScopeApproval,
    TaskMutation,
    TaskRequest,
)

app = typer.Typer(no_args_is_help=True, help="Local decision consistency for Git worktrees.")


@app.callback()
def options(ctx: typer.Context, root: Path = Path("."), state: Path | None = None) -> None:
    ctx.obj = {"root": root.resolve(), "state": state}


def service(ctx: typer.Context) -> Service:
    return Service(state_dir(ctx.obj["root"], ctx.obj["state"]))


def emit(value: dict[str, Any]) -> None:
    typer.echo(json.dumps(value, sort_keys=True, ensure_ascii=True))


def payload(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GuardError("INVALID", "Request must be a JSON object")
    return value


@app.command()
def init(ctx: typer.Context, coordinator: str, runner: Path) -> None:
    """Initialize with a reviewed RunnerConfig JSON file."""
    directory = initialize(
        ctx.obj["root"], ctx.obj["state"], coordinator, RunnerConfig.model_validate(payload(runner))
    )
    emit(envelope(state=str(directory)))


@app.command()
def status(ctx: typer.Context) -> None:
    emit(service(ctx).context())


@app.command("approve-task-scope")
def approve_task_scope(ctx: typer.Context, request: Path) -> None:
    """Coordinator approval of new or changed task scope."""
    emit(service(ctx).approve_scope(ScopeApproval.model_validate(payload(request))))


@app.command("migrate")
def migrate_command(ctx: typer.Context, sessions_stopped: bool = False) -> None:
    """Back up and migrate v1 state after stopping all CLI/MCP sessions."""
    emit(
        envelope(
            **migrate(
                state_dir(ctx.obj["root"], ctx.obj["state"]), sessions_stopped=sessions_stopped
            )
        )
    )


@app.command("prune-receipts")
def prune_receipts(ctx: typer.Context, days: int = 30, keep: int = 1000) -> None:
    """Explicit local maintenance; retain decision, validation and retry history."""
    from datetime import UTC, datetime, timedelta

    from decisionguard.domain.errors import require

    require(days >= 1 and keep >= 1, "INVALID", "Positive retention limits required")
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    local = service(ctx)
    with local.store.transaction() as db:
        cursor = db.execute(
            "DELETE FROM entities WHERE kind='receipt' AND json_extract(body,'$.timestamp') < ? "
            "AND id NOT IN (SELECT id FROM entities WHERE kind='receipt' "
            "ORDER BY json_extract(body,'$.timestamp') DESC,id DESC LIMIT ?)",
            (cutoff, keep),
        )
        deleted = cursor.rowcount
    emit(envelope(deleted=deleted))


@app.command()
def context(ctx: typer.Context, task_id: str | None = None) -> None:
    emit(service(ctx).context(task_id))


@app.command()
def task(ctx: typer.Context, request: Path) -> None:
    emit(service(ctx).register(TaskRequest.model_validate(payload(request))))


@app.command()
def assume(ctx: typer.Context, request: Path) -> None:
    emit(service(ctx).assume(AssumeRequest.model_validate(payload(request))))


@app.command()
def propose(ctx: typer.Context, request: Path) -> None:
    emit(service(ctx).propose(ProposeRequest.model_validate(payload(request))))


@app.command()
def review(ctx: typer.Context, request: Path) -> None:
    emit(service(ctx).review(ReviewRequest.model_validate(payload(request))))


@app.command()
def mapping(ctx: typer.Context, request: Path) -> None:
    """Record an explicitly reviewed compatibility/conversion mapping."""
    emit(service(ctx).mapping(MappingRequest.model_validate(payload(request))))


@app.command()
def events(ctx: typer.Context, task_id: str, actor: str, after: int = 0, limit: int = 100) -> None:
    emit(service(ctx).poll(task_id, actor, after, limit))


@app.command()
def ack(ctx: typer.Context, request: Path) -> None:
    emit(service(ctx).ack(AckRequest.model_validate(payload(request))))


@app.command()
def refresh(ctx: typer.Context, request: Path) -> None:
    emit(service(ctx).refresh(TaskMutation.model_validate(payload(request))))


@app.command()
def conflicts(ctx: typer.Context, task_id: list[str] | None = None) -> None:
    emit(service(ctx).conflicts(task_id))


@app.command("validate")
def validate_command(ctx: typer.Context, request: Path) -> None:
    result = validate(service(ctx), TaskMutation.model_validate(payload(request)))
    emit(result)
    if result["run"]["status"] == "error":
        raise typer.Exit(2)
    if not result["run"]["passed"] or not result["run"]["valid"]:
        raise typer.Exit(1)


@app.command("gate")
def gate_command(
    ctx: typer.Context, task_id: list[str] = typer.Option(...), integration_task: str | None = None
) -> None:
    result = gate(service(ctx), task_id, integration_task)
    emit(result)
    if not result["receipt"]["passed"]:
        raise typer.Exit(1)


@app.command("export")
def export_command(ctx: typer.Context, output: Path) -> None:
    output.write_text(json.dumps(export_metadata(service(ctx)), indent=2), encoding="utf-8")
    emit(envelope(exported=str(output)))


@app.command("import")
def import_command(ctx: typer.Context, request: Path, metadata: Path) -> None:
    emit(
        import_metadata(service(ctx), Mutation.model_validate(payload(request)), payload(metadata))
    )


@app.command()
def demo(destination: Path | None = None) -> None:
    """Run deterministic agents in disposable real Git worktrees."""
    from decisionguard.demo import run_demo

    emit(run_demo(destination))


@app.command()
def benchmark() -> None:
    from decisionguard.reports.benchmark import evaluate

    result = evaluate()
    emit(result)
    if (
        result["correctly_classified"] != result["classification_count"]
        or result["lifecycle_passed"] != result["lifecycle_count"]
    ):
        raise typer.Exit(1)


def main() -> None:
    try:
        app()
    except (GuardError, ValidationError, OSError, ValueError, sqlite3.Error) as exc:
        code = exc.code if isinstance(exc, GuardError) else "INVALID"
        # Do not echo full Pydantic inputs (which may contain sensitive material).
        message = (
            exc.message
            if isinstance(exc, GuardError)
            else f"{type(exc).__name__}: operation failed"
        )
        emit(envelope(error={"code": code, "message": message}))
        sys.exit(2)


if __name__ == "__main__":
    main()
