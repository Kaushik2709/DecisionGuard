import json
import os
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path

from decisionguard.domain.errors import require
from decisionguard.domain.models import Config, RunnerConfig
from decisionguard.git.context import common_dir, repository_root
from decisionguard.storage.locking import exclusive_lock
from decisionguard.storage.migrations import EPOCH_TRIGGERS, V3
from decisionguard.storage.sqlite import Store


def state_dir(root: Path, explicit: Path | None = None) -> Path:
    common = common_dir(root)
    if explicit is not None:
        require(
            common is None or explicit.resolve() == common / "decisionguard",
            "INVALID",
            "Git repositories must use their canonical shared state directory",
        )
        return explicit.resolve()
    require(common is not None, "INVALID", "Non-Git projects require --state")
    assert common is not None
    return common / "decisionguard"


def initialize(root: Path, state: Path | None, coordinator: str, runner: RunnerConfig) -> Path:
    root = root.resolve()
    require(root.is_dir(), "INVALID", "Project root does not exist")
    common = common_dir(root)
    if common:
        root = repository_root(root)
    directory = state_dir(root, state)
    directory.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(directory / "admin.lock"), exclusive_lock(directory / "activity.lock"):
        require(not (directory / "config.json").exists(), "INVALID", "Already initialized")
        journal = directory / "initialization.json"
        if journal.exists():
            config = Config.model_validate_json(journal.read_text(encoding="utf-8"))
            require(
                config.root == str(root)
                and config.common_dir == (str(common) if common else None)
                and config.coordinators == [coordinator]
                and config.runner == runner,
                "INVALID",
                "Retry initialization with its original root, coordinator and runner",
            )
        else:
            require(
                not (directory / "state.db").exists(),
                "INVALID",
                "Existing database without initialization journal; recover manually",
            )
            config = Config(
                project=str(uuid.uuid4()),
                root=str(root),
                common_dir=str(common) if common else None,
                coordinators=[coordinator],
                runner=runner,
            )
            atomic_json(journal, config.model_dump_json(indent=2))
        Store(directory / "state.db", config.project, create=True)
        atomic_json(directory / "config.json", config.model_dump_json(indent=2))
    return directory


def atomic_json(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def migrate(directory: Path, *, sessions_stopped: bool) -> dict[str, str | int]:
    require(sessions_stopped, "INVALID", "Stop all CLI/MCP sessions and pass --sessions-stopped")
    config = load_config(directory)
    with exclusive_lock(directory / "admin.lock"), exclusive_lock(directory / "activity.lock"):
        require((directory / "state.db").is_file(), "NOT_FOUND", "Missing state database")
        db = sqlite3.connect(directory / "state.db", isolation_level=None, timeout=5)
        try:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            require(version in (1, 2, 3), "INVALID", "Unsupported database schema")
            require(
                db.execute("SELECT value FROM meta WHERE key='project'").fetchone()[0]
                == config.project,
                "FORBIDDEN",
                "Foreign project database",
            )
            if version == 3:
                return {"database_version": 3, "status": "already_current"}
            backup = directory / f"state-v{version}-backup-{uuid.uuid4().hex}.db"
            with closing(sqlite3.connect(backup)) as target:
                db.backup(target)
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT OR IGNORE INTO meta VALUES('state_epoch','0')")
                for trigger in EPOCH_TRIGGERS:
                    db.execute(trigger)
                for kind, identity, raw in db.execute(
                    "SELECT kind,id,body FROM entities WHERE kind IN ('task','run')"
                ).fetchall():
                    body = json.loads(raw)
                    if kind == "task" and version == 1:
                        body.update(
                            evidence_generation=1,
                            run_sequence=0,
                            latest_run_id=None,
                            scope_revision=0,
                            scope_approved=False,
                        )
                    elif kind == "task":
                        body["evidence_generation"] += 1
                    else:
                        body["valid"] = False
                    db.execute(
                        "UPDATE entities SET body=? WHERE kind=? AND id=?",
                        (json.dumps(body), kind, identity),
                    )
                for statement in V3:
                    db.execute(statement)
                db.execute("PRAGMA user_version=3")
                db.commit()
            except BaseException:
                db.rollback()
                raise
            return {"database_version": 3, "backup": str(backup), "status": "migrated"}
        finally:
            db.close()


def load_config(directory: Path) -> Config:
    path = directory / "config.json"
    require(path.is_file(), "NOT_FOUND", "Initialize DecisionGuard first")
    return Config.model_validate(json.loads(path.read_text(encoding="utf-8")))
