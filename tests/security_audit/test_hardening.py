import json
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import CONTRACT, MAJOR, accept, key, proposal

from decisionguard.application.config import initialize, migrate
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AssumeRequest,
    ResourceLimits,
    RunnerConfig,
    ScopeApproval,
    TaskMutation,
    TaskRequest,
)
from decisionguard.storage.locking import exclusive_lock
from decisionguard.storage.sqlite import get, put
from decisionguard.validation.snapshot import stable_capture


def run(service, token=None):
    return validate(
        service, TaskMutation(actor="worker", task_id="worker", idempotency_key=token or key())
    )


def test_mcp_scope_requires_operator_approval(project):
    service, root = project
    worker = Service(service.directory, session_actor="worker")
    worker.register(
        TaskRequest(
            actor="worker",
            task_id="mcp-task",
            paths=["code.py"],
            contracts=[CONTRACT],
            worktree=str(root),
            idempotency_key=key(),
        )
    )
    with pytest.raises(GuardError, match="awaits"):
        validate(service, TaskMutation(actor="worker", task_id="mcp-task", idempotency_key=key()))
    request = ScopeApproval(
        actor="coordinator",
        task_id="mcp-task",
        paths=["code.py"],
        expected_scope_revision=0,
        idempotency_key=key(),
    )
    service.approve_scope(request)
    assert service.approve_scope(request)["task"]["scope_revision"] == 1
    with pytest.raises(GuardError, match="scope changed"):
        service.approve_scope(request.model_copy(update={"idempotency_key": key()}))
    result = validate(
        service, TaskMutation(actor="worker", task_id="mcp-task", idempotency_key=key())
    )
    assert result["run"]["passed"]


@pytest.mark.parametrize("mutation", ["assume", "scope"])
def test_mutations_during_validation_invalidate_generation(project, monkeypatch, mutation):
    service, _ = project
    import decisionguard.application.validation as module

    original = module.execute
    ready, resume = threading.Event(), threading.Event()

    def execute(root, config):
        result = original(root, config)
        ready.set()
        assert resume.wait(15)
        return result

    monkeypatch.setattr(module, "execute", execute)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run, service)
        try:
            assert ready.wait(15)
            if mutation == "assume":
                service.assume(
                    AssumeRequest(
                        actor="worker",
                        task_id="worker",
                        contract=CONTRACT,
                        expected=MAJOR,
                        observed_version=1,
                        idempotency_key=key(),
                    )
                )
            else:
                service.approve_scope(
                    ScopeApproval(
                        actor="coordinator",
                        task_id="worker",
                        paths=["code.py", "check.py"],
                        expected_scope_revision=0,
                        idempotency_key=key(),
                    )
                )
        finally:
            resume.set()
        assert not future.result(timeout=20)["run"]["valid"]
    assert not gate(service, ["worker"])["receipt"]["passed"]


def test_older_run_finishing_after_new_failure_cannot_win(project, monkeypatch):
    service, _ = project
    import decisionguard.application.validation as module

    ready, resume = threading.Event(), threading.Event()
    counter = 0
    mutex = threading.Lock()

    def execute(root, config):
        nonlocal counter
        with mutex:
            counter += 1
            first = counter == 1
        if first:
            ready.set()
            assert resume.wait(15)
        return {"passed": first, "exit_code": 0 if first else 1, "output": "", "timed_out": False}

    monkeypatch.setattr(module, "execute", execute)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(run, service)
        try:
            assert ready.wait(15)
            second = run(service)["run"]
            assert second["sequence"] == 2 and not second["passed"]
        finally:
            resume.set()
        assert not first.result(timeout=20)["run"]["valid"]
    assert not gate(service, ["worker"])["receipt"]["passed"]


@pytest.mark.parametrize("status", ["error", "executing", "timeout"])
def test_latest_unusable_attempt_blocks_old_success(project, monkeypatch, status):
    service, _ = project
    assert run(service)["run"]["passed"]
    import decisionguard.application.validation as module

    def execute(root, config):
        if status == "error":
            raise OSError("Injected runner error")
        if status == "executing":
            raise KeyboardInterrupt("Injected process interruption")
        return {"passed": False, "exit_code": -1, "timed_out": True, "output": ""}

    monkeypatch.setattr(module, "execute", execute)
    if status == "executing":
        with pytest.raises(KeyboardInterrupt):
            run(service)
    else:
        assert not run(service)["run"]["passed"]
    assert not gate(service, ["worker"])["receipt"]["passed"]


def test_transactional_pending_quota_and_idempotent_retry(project):
    service, _ = project
    config = service.config.model_copy(update={"limits": ResourceLimits(pending_per_actor=1)})
    (service.directory / "config.json").write_text(config.model_dump_json())
    barrier = threading.Barrier(2)

    def submit():
        barrier.wait(timeout=10)
        try:
            return proposal(Service(service.directory))
        except GuardError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        outcomes = [future.result(timeout=20) for future in futures]
    assert outcomes.count("RESOURCE_LIMIT") == 1
    accepted = next(item for item in outcomes if isinstance(item, dict))
    accept(service, accepted, accept=False)
    assert proposal(service)["proposal"]["status"] == "pending"


@pytest.mark.parametrize(
    "limit", ["snapshot_files", "snapshot_file_bytes", "snapshot_total_bytes", "snapshot_seconds"]
)
def test_snapshot_limits_fail_closed(project, limit):
    service, root = project
    limits = ResourceLimits(**{limit: 0.000001 if limit == "snapshot_seconds" else 1})
    with pytest.raises(GuardError) as error:
        stable_capture(root, [], service.directory, limits)
    assert error.value.code == "RESOURCE_LIMIT"


def test_gate_capture_does_not_hold_writer_lock(project, monkeypatch):
    service, _ = project
    run(service)
    import decisionguard.application.validation as module

    original = module.stable_capture
    calls = 0

    def capture(*args, **kwargs):
        nonlocal calls
        calls += 1
        # A second connection must acquire a writer lock during every capture.
        with service.store.transaction() as db:
            if calls == 2:
                task = get(db, "task", "worker")
                task["evidence_generation"] += 1
                put(db, "task", "worker", task)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "stable_capture", capture)
    receipt = gate(service, ["worker"])["receipt"]
    assert calls == 2 and not receipt["passed"]
    assert any(item["kind"] == "state_changed" for item in receipt["findings"])


def test_migration_preserves_history_and_requires_new_approval_and_evidence(project, tmp_path):
    service, _ = project
    run(service)
    before = service.context()["decisions"]
    with service.store.connect() as db:
        db.execute("PRAGMA user_version=1")
    service.close()
    with pytest.raises(GuardError, match="Stop all"):
        migrate(service.directory, sessions_stopped=False)
    result = migrate(service.directory, sessions_stopped=True)
    with sqlite3.connect(result["backup"]) as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 1
        # Exercise SQLite restore into a disposable database, not the live state.
        with sqlite3.connect(tmp_path / "restored.db") as restored:
            backup.backup(restored)
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 1
    current = Service(service.directory)
    assert current.context()["decisions"] == before
    assert not gate(current, ["worker"])["receipt"]["passed"]
    current.approve_scope(
        ScopeApproval(
            actor="coordinator",
            task_id="worker",
            paths=["code.py", "check.py"],
            expected_scope_revision=0,
            idempotency_key=key(),
        )
    )
    assert run(current)["run"]["valid"]
    assert gate(current, ["worker"])["receipt"]["passed"]
    current.close()
    assert migrate(service.directory, sessions_stopped=True)["status"] == "already_current"


def test_migration_rollback_keeps_v1_on_corruption(project):
    service, _ = project
    with service.store.connect() as db:
        db.execute("PRAGMA user_version=1")
        for name in (
            "entity_active_actor",
            "entity_task_actor",
            "entity_proposal_status",
            "entity_assumption_task",
        ):
            db.execute(f"DROP INDEX {name}")
        db.execute("UPDATE entities SET body='invalid-json' WHERE kind='task'")
    service.close()
    with pytest.raises(json.JSONDecodeError):
        migrate(service.directory, sessions_stopped=True)
    with sqlite3.connect(service.directory / "state.db") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
    assert list(service.directory.glob("state-v1-backup-*.db"))


def test_admin_lock_rejects_concurrent_initialization(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    state = root / "state"
    with exclusive_lock(state / "admin.lock"):
        with pytest.raises(GuardError) as error:
            initialize(
                root, state, "coordinator", RunnerConfig(argv=[sys.executable, "-c", "pass"])
            )
        assert error.value.code == "BUSY"
    assert (
        initialize(root, state, "coordinator", RunnerConfig(argv=[sys.executable, "-c", "pass"]))
        == state
    )
