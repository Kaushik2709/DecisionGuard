import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from decisionguard.domain.errors import GuardError, require
from decisionguard.storage.migrations import EPOCH_TRIGGERS, SCHEMA, V3


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class Store:
    def __init__(self, path: Path, project: str, *, create: bool = False):
        self.path = path
        self.project = project
        require(create or path.is_file(), "NOT_FOUND", "Initialize DecisionGuard first")
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self.connect() as db:
                version = db.execute("PRAGMA user_version").fetchone()[0]
                require(version in (0, 3), "MIGRATION_REQUIRED", "Run decisionguard migrate")
                db.executescript(SCHEMA)
                db.execute("PRAGMA user_version=3")
                for statement in V3:
                    db.execute(statement)
                db.execute("INSERT OR IGNORE INTO meta VALUES('project',?)", (project,))
                db.execute("INSERT OR IGNORE INTO meta VALUES('revision','0')")
                db.execute("INSERT OR IGNORE INTO meta VALUES('state_epoch','0')")
                for trigger in EPOCH_TRIGGERS:
                    db.execute(trigger)
                db.commit()
        with self.connect() as db:
            require(
                db.execute("PRAGMA user_version").fetchone()[0] == 3,
                "MIGRATION_REQUIRED",
                "Unsupported database schema; run decisionguard migrate for v1",
            )
            row = db.execute("SELECT value FROM meta WHERE key='project'").fetchone()
            require(row is not None and row[0] == project, "FORBIDDEN", "Foreign project database")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        try:
            db.execute("PRAGMA journal_mode=WAL")
            yield db
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc) or "busy" in str(exc):
                raise GuardError(
                    "BUSY", "Database busy after bounded wait; retry same request"
                ) from exc
            raise
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise


def get(db: sqlite3.Connection, kind: str, identity: str) -> dict[str, Any]:
    row = db.execute("SELECT body FROM entities WHERE kind=? AND id=?", (kind, identity)).fetchone()
    require(row is not None, "NOT_FOUND", f"Unknown {kind}: {identity}")
    return dict(json.loads(row[0]))


def put(db: sqlite3.Connection, kind: str, identity: str, body: dict[str, Any]) -> None:
    db.execute(
        "INSERT INTO entities VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
        (kind, identity, dumps(body)),
    )


def all_entities(db: sqlite3.Connection, kind: str) -> list[dict[str, Any]]:
    return [
        json.loads(row[0])
        for row in db.execute("SELECT body FROM entities WHERE kind=? ORDER BY id", (kind,))
    ]


def revision(db: sqlite3.Connection) -> int:
    return int(db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0])


def heads(db: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    return {
        row[0]: json.loads(row[1])
        for row in db.execute(
            "SELECT h.contract,v.body FROM heads h JOIN versions v "
            "ON h.contract=v.contract AND h.version=v.version"
        )
    }
