import sqlite3

import pytest
from conftest import key

from decisionguard.application.config import migrate
from decisionguard.application.operations import archive, backup, doctor, restore_backup
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import ResourceLimits, TaskMutation, TaskRequest


def test_backup_restore_rejects_live_sessions_and_invalidates_evidence(project, tmp_path):
    service, _ = project
    request = TaskMutation(actor="worker", task_id="worker", idempotency_key=key())
    assert validate(service, request)["run"]["passed"]
    path = tmp_path / "backup.db"
    backup(service, path)
    assert doctor(service)["ok"]
    with pytest.raises(GuardError) as error:
        restore_backup(service.directory, path, sessions_stopped=True)
    assert error.value.code == "BUSY"
    service.close()
    result = restore_backup(service.directory, path, sessions_stopped=True)
    assert result["fresh_validation_required"]
    current = Service(service.directory)
    assert not gate(current, ["worker"])["receipt"]["passed"]
    assert current.context()["decisions"]


def test_archive_frees_active_quota_restore_requires_evidence(project):
    service, root = project
    request = TaskMutation(actor="worker", task_id="worker", idempotency_key=key())
    assert archive(service, request)["task"]["archived"]
    assert archive(service, request)["task"]["archived"]
    config = service.config.model_copy(update={"limits": ResourceLimits(tasks_per_actor=1)})
    (service.directory / "config.json").write_text(config.model_dump_json())
    service.register(
        TaskRequest(
            actor="worker",
            task_id="next",
            worktree=str(root),
            paths=["code.py"],
            idempotency_key=key(),
        )
    )
    with pytest.raises(GuardError) as error:
        archive(service, request.model_copy(update={"idempotency_key": key()}), restore=True)
    assert error.value.code == "RESOURCE_LIMIT"


def test_v2_migration_blocks_live_session_and_preserves_backup(project):
    service, _ = project
    with service.store.connect() as db:
        db.execute("PRAGMA user_version=2")
    with pytest.raises(GuardError) as error:
        migrate(service.directory, sessions_stopped=True)
    assert error.value.code == "BUSY"
    service.close()
    result = migrate(service.directory, sessions_stopped=True)
    assert result["database_version"] == 3
    with sqlite3.connect(result["backup"]) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
