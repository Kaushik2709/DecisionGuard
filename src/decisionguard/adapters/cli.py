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
contracts_app = typer.Typer(help="Preview and propose reviewed local OpenAPI contracts.")
app.add_typer(contracts_app, name="contracts")
advice_app = typer.Typer(help="Optional advisory classification. No effect on gate clearance.")
app.add_typer(advice_app, name="advice")
setup_app = typer.Typer(help="Review client configuration without changing global settings.")
app.add_typer(setup_app, name="setup")
evaluation_app = typer.Typer(help="Local paired product studies; no commands or model calls.")
app.add_typer(evaluation_app, name="evaluation")
reliability_app = typer.Typer(help="Disposable local recovery and performance workloads.")
app.add_typer(reliability_app, name="reliability")


@app.callback()
def options(ctx: typer.Context, root: Path = Path("."), state: Path | None = None) -> None:
    ctx.obj = {"root": root.resolve(), "state": state}


def service(ctx: typer.Context) -> Service:
    return Service(state_dir(ctx.obj["root"], ctx.obj["state"]))


def emit(value: dict[str, Any]) -> None:
    typer.echo(json.dumps(value, sort_keys=True, ensure_ascii=True))


def payload(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 16 * 1024 * 1024:
        raise GuardError("RESOURCE_LIMIT", "JSON request exceeds 16 MiB")
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


@app.command()
def doctor(ctx: typer.Context) -> None:
    from decisionguard.application.operations import doctor as diagnose

    local = service(ctx)
    try:
        result = diagnose(local)
        emit(result)
        if not result["ok"]:
            raise typer.Exit(1)
    finally:
        local.close()


@app.command("archive-task")
def archive_task(ctx: typer.Context, request: Path) -> None:
    from decisionguard.application.operations import archive

    emit(archive(service(ctx), TaskMutation.model_validate(payload(request))))


@app.command("restore-task")
def restore_task(ctx: typer.Context, request: Path) -> None:
    from decisionguard.application.operations import archive

    emit(archive(service(ctx), TaskMutation.model_validate(payload(request)), restore=True))


@app.command()
def backup(ctx: typer.Context, destination: Path) -> None:
    from decisionguard.application.operations import backup as save

    emit(save(service(ctx), destination))


@app.command("restore-backup")
def restore_backup(ctx: typer.Context, source: Path, sessions_stopped: bool = False) -> None:
    from decisionguard.application.operations import restore_backup as restore

    emit(
        restore(
            state_dir(ctx.obj["root"], ctx.obj["state"]), source, sessions_stopped=sessions_stopped
        )
    )


@app.command()
def maintain(ctx: typer.Context, apply: bool = False, days: int = 30) -> None:
    from decisionguard.application.operations import maintain as prune

    emit(prune(service(ctx), apply=apply, days=days))


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


@contracts_app.command("scan")
def contracts_scan(ctx: typer.Context, request: Path) -> None:
    from decisionguard.application.contracts import scan
    from decisionguard.domain.contracts import ContractScan

    emit(scan(service(ctx), ContractScan.model_validate(payload(request))))


@contracts_app.command("propose")
def contracts_propose(ctx: typer.Context, request: Path) -> None:
    from decisionguard.application.contracts import publish
    from decisionguard.domain.contracts import ContractPublish

    emit(publish(service(ctx), ContractPublish.model_validate(payload(request))))


@advice_app.command("preview")
def advice_preview(ctx: typer.Context, request: Path, output: Path) -> None:
    from decisionguard.application.advisories import preview
    from decisionguard.domain.advisories import AdviceRequest

    result = preview(service(ctx), AdviceRequest.model_validate(payload(request)))
    require_new = not output.exists()
    if not require_new:
        raise GuardError("INVALID", "Choose a new preview output file")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    emit(result)


@advice_app.command("classify")
def advice_classify(ctx: typer.Context, preview: Path) -> None:
    from decisionguard.application.advisories import classify

    if preview.stat().st_size > 262144:
        raise GuardError("RESOURCE_LIMIT", "Preview file exceeds 256 KiB")
    result = classify(service(ctx), payload(preview))
    emit(result)
    if result["advisory"]["status"] != "available":
        raise typer.Exit(2)


@advice_app.command("list")
def advice_list(ctx: typer.Context, task_id: str, limit: int = 100) -> None:
    from decisionguard.application.advisories import list_advisories

    emit(list_advisories(service(ctx), task_id, limit))


@advice_app.command("evaluate")
def advice_evaluate(ctx: typer.Context, dataset: Path) -> None:
    from decisionguard.reports.advisory_evaluation import EvaluationDataset, evaluate

    if dataset.stat().st_size > 10 * 1024 * 1024:
        raise GuardError("RESOURCE_LIMIT", "Evaluation dataset exceeds 10 MiB")
    emit(evaluate(service(ctx), EvaluationDataset.model_validate(payload(dataset))))


@evaluation_app.command("schema")
def evaluation_schema() -> None:
    from decisionguard.domain.product_evaluation import StudyObservations, StudyPlan

    emit(
        envelope(
            plan=StudyPlan.model_json_schema(), observations=StudyObservations.model_json_schema()
        )
    )


@reliability_app.command("recovery")
def reliability_recovery(destination: Path) -> None:
    from decisionguard.reports.reliability import recovery_drill

    emit(recovery_drill(destination))


@reliability_app.command("filesystem-full")
def reliability_filesystem_full(destination: Path) -> None:
    from decisionguard.reports.reliability import filesystem_full_drill

    emit(filesystem_full_drill(destination))


@reliability_app.command("soak")
def reliability_soak(
    destination: Path, seconds: float = 30, workers: int = 2, history: int = 1000
) -> None:
    from decisionguard.reports.reliability import soak

    result = soak(destination, seconds=seconds, workers=workers, history=history)
    emit(result)
    if not result["passed"]:
        raise typer.Exit(1)


@evaluation_app.command("plan")
def evaluation_plan(plan: Path) -> None:
    """Inspect a fixed plan and its label evidence; print its canonical digest."""
    from decisionguard.application.product_evaluation import inspect_plan

    emit(inspect_plan(plan))


@evaluation_app.command("report")
def evaluation_report(plan: Path, observations: Path) -> None:
    """Verify local evidence and report matched outcomes; requires no initialized database."""
    from decisionguard.application.product_evaluation import evaluate_files

    emit(evaluate_files(plan, observations))


@evaluation_app.command("kit")
def evaluation_kit(plan: Path, destination: Path) -> None:
    """Prepare a portable study archive and feedback instructions; collect no responses."""
    from decisionguard.application.product_evaluation import create_pilot_kit

    emit(create_pilot_kit(plan, destination))


@setup_app.command("codex")
def setup_codex(ctx: typer.Context, actor: str) -> None:
    from decisionguard.application.setup import codex_preview

    emit(codex_preview(service(ctx), actor))


@setup_app.command("project")
def setup_project_command(ctx: typer.Context, request: Path, apply: bool = False) -> None:
    """Preview setup intent; --apply initializes/registers with resumable idempotency."""
    from decisionguard.application.onboarding import setup_project
    from decisionguard.domain.onboarding import ProjectSetup

    emit(
        setup_project(
            ctx.obj["root"],
            ctx.obj["state"],
            ProjectSetup.model_validate(payload(request)),
            apply=apply,
        )
    )


@app.command("next")
def next_command(
    ctx: typer.Context, task_id: list[str] = typer.Option(...), integration_task: str | None = None
) -> None:
    """Assess current source and show next actions without persisting a receipt."""
    from decisionguard.application.onboarding import next_actions

    local = service(ctx)
    try:
        result = next_actions(local, task_id, integration_task)
        emit(result)
        if not result["scope_passed"]:
            raise typer.Exit(1)
    finally:
        local.close()


@app.command()
def impact(ctx: typer.Context, task_id: list[str] | None = None) -> None:
    emit(service(ctx).impact(task_id))


@app.command()
def watch(ctx: typer.Context, task_id: str, actor: str, after: int = 0, once: bool = False) -> None:
    import time

    local = service(ctx)
    try:
        while True:
            result = local.poll(task_id, actor, after=after)
            if result["events"] or once:
                emit(result)
            if result["events"]:
                after = result["events"][-1]["event_id"]
            if once:
                return
            time.sleep(1)
    finally:
        local.close()


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
