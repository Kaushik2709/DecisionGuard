"""Explicit local maintenance. No model calls and no implicit deletion of history."""

import json
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from decisionguard.application.config import load_config
from decisionguard.application.services import Service, envelope, now
from decisionguard.domain.errors import require
from decisionguard.domain.models import TaskMutation
from decisionguard.storage.locking import exclusive_lock
from decisionguard.storage.sqlite import dumps, get, put


def archive(service: Service, request: TaskMutation, *, restore: bool = False) -> dict[str, Any]:
    def action(db: sqlite3.Connection) -> dict[str, Any]:
        task = get(db, "task", request.task_id)
        require(task["actor"] == request.actor, "FORBIDDEN", "Task belongs to another actor")
        service.worktree(Path(task["worktree"]))
        if restore:
            require(task.get("archived", False), "INVALID", "Task is not archived")
            count = db.execute(
                "SELECT COUNT(*) FROM entities WHERE kind='task' AND "
                "COALESCE(json_extract(body,'$.archived'),0)=0"
            ).fetchone()[0]
            actor_count = db.execute(
                "SELECT COUNT(*) FROM entities WHERE kind='task' AND "
                "json_extract(body,'$.actor')=? AND COALESCE(json_extract(body,'$.archived'),0)=0",
                (request.actor,),
            ).fetchone()[0]
            require(
                count < service.config.limits.tasks_per_project
                and actor_count < service.config.limits.tasks_per_actor,
                "RESOURCE_LIMIT",
                "Task quota reached",
            )
        else:
            require(not task.get("archived", False), "INVALID", "Task is already archived")
            pending = db.execute(
                "SELECT 1 FROM entities WHERE kind='proposal' AND "
                "json_extract(body,'$.task_id')=? AND json_extract(body,'$.status')='pending'",
                (request.task_id,),
            ).fetchone()
            require(not pending, "INVALID", "Resolve this task's pending proposals before archival")
        task["archived"] = not restore
        put(db, "task", request.task_id, task)
        service.invalidate(db, request.task_id)
        if restore:
            service.bootstrap_notices(db, task)
        service.emit(
            db,
            request.task_id,
            "restored" if restore else "archived",
            {"generation": get(db, "task", request.task_id)["evidence_generation"]},
        )
        return {"task": get(db, "task", request.task_id), "fresh_validation_required": True}

    return service.mutate("restore_task" if restore else "archive_task", request, action)


def backup(service: Service, destination: Path) -> dict[str, Any]:
    destination = destination.resolve()
    require(
        not destination.exists() and not destination.with_suffix(".config.json").exists(),
        "INVALID",
        "Backup destination must be new",
    )
    require(destination.parent.is_dir(), "INVALID", "Backup parent does not exist")
    with destination.open("xb"):
        pass
    with service.store.connect() as source, closing(sqlite3.connect(destination)) as target:
        source.backup(target)
        require(
            target.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "INVALID",
            "Backup failed integrity check",
        )
    destination.with_suffix(".config.json").write_text(
        service.config.model_dump_json(indent=2), encoding="utf-8"
    )
    return envelope(backup=str(destination), database_version=3, timestamp=now())


def restore_backup(directory: Path, source: Path, *, sessions_stopped: bool) -> dict[str, Any]:
    require(sessions_stopped, "INVALID", "Stop all sessions and pass --sessions-stopped")
    config = load_config(directory)
    source = source.resolve()
    require(
        source.is_file() and source != (directory / "state.db").resolve(),
        "INVALID",
        "Select a separate backup",
    )
    with exclusive_lock(directory / "admin.lock"), exclusive_lock(directory / "activity.lock"):
        with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as saved:
            require(
                saved.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "INVALID",
                "Corrupt backup",
            )
            require(
                saved.execute("PRAGMA user_version").fetchone()[0] == 3,
                "MIGRATION_REQUIRED",
                "Restore requires a schema 3 backup",
            )
            require(
                saved.execute("SELECT value FROM meta WHERE key='project'").fetchone()[0]
                == config.project,
                "FORBIDDEN",
                "Foreign project backup",
            )
            # Invalidate a disposable copy FIRST. A crash must not restore passing evidence.
            with tempfile.TemporaryDirectory(prefix="restore-stage-", dir=directory) as staging:
                with closing(sqlite3.connect(Path(staging) / "stage.db")) as prepared:
                    saved.backup(prepared)
                    _invalidate_restored(prepared)
                    rollback = directory / f"pre-restore-{uuid.uuid4().hex}.db"
                    with closing(sqlite3.connect(directory / "state.db")) as live:
                        with closing(sqlite3.connect(rollback)) as target:
                            live.backup(target)
                        prepared.backup(live)
    return envelope(restored=True, rollback_backup=str(rollback), fresh_validation_required=True)


def _invalidate_restored(live: sqlite3.Connection) -> None:
    for identity, raw in live.execute("SELECT id,body FROM entities WHERE kind='task'").fetchall():
        task = json.loads(raw)
        task["evidence_generation"] += 1
        task["latest_run_id"] = None
        live.execute(
            "UPDATE entities SET body=? WHERE kind='task' AND id=?",
            (dumps(task), identity),
        )
    live.execute("UPDATE entities SET body=json_set(body,'$.valid',json('false')) WHERE kind='run'")
    live.commit()


def maintain(service: Service, *, apply: bool = False, days: int = 30) -> dict[str, Any]:
    require(days >= 1, "INVALID", "Positive retention required")
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with service.store.transaction() as db:
        rows = db.execute(
            "SELECT id,body FROM entities WHERE kind='run' AND "
            "json_extract(body,'$.timestamp')<? AND json_extract(body,'$.status')!='executing' "
            "AND id NOT IN (SELECT json_extract(body,'$.latest_run_id') FROM entities "
            "WHERE kind='task' AND json_extract(body,'$.latest_run_id') IS NOT NULL)",
            (cutoff,),
        ).fetchall()
        changed = 0
        for identity, raw in rows:
            body = json.loads(raw)
            if "output" in body:
                changed += 1
                if apply:
                    body.pop("output")
                    body["output_pruned"] = True
                    put(db, "run", identity, body)
    return envelope(
        preview=not apply,
        eligible_run_outputs=changed,
        retention_days=days,
        preserved=["decisions", "events", "idempotency", "latest_runs"],
    )


def doctor(service: Service) -> dict[str, Any]:
    with service.store.connect() as db:
        integrity = db.execute("PRAGMA quick_check").fetchone()[0]
        version = db.execute("PRAGMA user_version").fetchone()[0]
    runners = [("default", None, service.config.runner)] + [
        ("task:" + name, name, runner) for name, runner in service.config.task_runners.items()
    ]
    available = {}
    for label, name, runner in runners:
        command = runner.argv[0]
        command_path = Path(command)
        with service.store.connect() as db:
            row = db.execute(
                "SELECT body FROM entities WHERE kind='task' AND id=?", (name,)
            ).fetchone()
        root = Path(json.loads(row[0])["worktree"]) if row else Path(service.config.root)
        cwd = (root / runner.cwd).resolve()
        if command_path.is_absolute():
            available[label] = command_path.is_file()
        elif "/" in command or "\\" in command:
            # Relative executables are resolved in the actual configured task cwd.
            available[label] = (cwd / command_path).is_file()
        else:
            available[label] = shutil.which(command) is not None
        available[label] = available[label] and cwd.is_dir() and cwd.is_relative_to(root.resolve())
    found = all(available.values())
    return envelope(
        ok=integrity == "ok" and found,
        database_version=version,
        database_integrity=integrity,
        runner_available=found,
        runners_available=available,
        project=service.config.project,
        state=str(service.directory),
        mcp_transport="stdio",
        automatic_agent_delivery=False,
        jev_enabled_by_default=False,
    )
