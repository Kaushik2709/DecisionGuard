import json
import subprocess
import sys


def cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "decisionguard.adapters.cli", *map(str, args)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, json.loads(result.stdout)


def test_cli_validation_gate_and_error_codes(project, tmp_path):
    _, root = project
    request = tmp_path / "validation request.json"
    request.write_text(
        json.dumps({"actor": "worker", "task_id": "worker", "idempotency_key": "cli-run"})
    )
    code, output = cli("--root", root, "validate", request)
    assert code == 0 and output["run"]["passed"]
    code, output = cli("--root", root, "gate", "--task-id", "worker")
    assert code == 0 and output["receipt"]["passed"]
    (root / "code.py").write_text("amount='changed'\n")
    code, output = cli("--root", root, "gate", "--task-id", "worker")
    assert code == 1 and not output["receipt"]["passed"]
    request.write_text('{"actor":"worker"}')
    code, output = cli("--root", root, "refresh", request)
    assert code == 2 and output["error"]["code"] == "INVALID"
    service, _ = project
    from decisionguard.domain.models import RunnerConfig

    config = service.config.model_copy(
        update={"runner": RunnerConfig(argv=[str(tmp_path / "missing-runner.exe")])}
    )
    (service.directory / "config.json").write_text(config.model_dump_json())
    request.write_text(
        json.dumps({"actor": "worker", "task_id": "worker", "idempotency_key": "missing-runner"})
    )
    code, output = cli("--root", root, "validate", request)
    assert code == 2 and output["run"]["status"] == "error"


def test_non_git_explicit_state_initialization(tmp_path):
    root = tmp_path / "non git project"
    root.mkdir()
    state = tmp_path / "state"
    runner = tmp_path / "runner.json"
    runner.write_text(json.dumps({"argv": [sys.executable, "-c", "print('checked')"]}))
    code, output = cli("--root", root, "--state", state, "init", "coordinator", runner)
    assert code == 0 and output["state"] == str(state.resolve())
    code, output = cli("--root", root, "--state", state, "status")
    assert code == 0 and output["revision"] == 0
    code, output = cli("--root", root, "status")
    assert code == 2 and output["error"]["code"] == "INVALID"


def test_administrative_migration_scope_and_pruning(project, tmp_path):
    from decisionguard.storage.sqlite import all_entities, put

    service, root = project
    with service.store.connect() as db:
        db.execute("PRAGMA user_version=1")
    code, result = cli("--root", root, "migrate")
    assert code == 2
    code, result = cli("--root", root, "migrate", "--sessions-stopped")
    assert code == 0 and result["database_version"] == 2
    request = tmp_path / "approve.json"
    request.write_text(
        json.dumps(
            {
                "actor": "coordinator",
                "task_id": "worker",
                "idempotency_key": "approve",
                "expected_scope_revision": 0,
                "paths": ["code.py", "check.py"],
            }
        )
    )
    code, result = cli("--root", root, "approve-task-scope", request)
    assert code == 0 and result["task"]["scope_approved"]
    with service.store.transaction() as db:
        for identity, timestamp in [
            ("old", "2000-01-01T00:00:00+00:00"),
            ("newer", "2001-01-01T00:00:00+00:00"),
        ]:
            put(db, "receipt", identity, {"receipt_id": identity, "timestamp": timestamp})
    code, result = cli("--root", root, "prune-receipts", "--days", 30, "--keep", 1)
    assert code == 0 and result["deleted"] == 1
    with service.store.connect() as db:
        assert [r["receipt_id"] for r in all_entities(db, "receipt")] == ["newer"]
        assert db.execute("SELECT COUNT(*) FROM versions").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM retries").fetchone()[0] > 0
