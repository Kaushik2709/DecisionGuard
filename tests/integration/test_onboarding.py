import sys

import pytest
from conftest import CONTRACT, accept, key, proposal

from decisionguard.application.onboarding import next_actions, setup_project
from decisionguard.application.operations import doctor
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import RunnerConfig, TaskMutation
from decisionguard.domain.onboarding import ProjectSetup


def test_preview_apply_and_retry_without_accepting_contracts(tmp_path):
    root = tmp_path / "non git project"
    root.mkdir()
    state = tmp_path / "state"
    request = ProjectSetup.model_validate(
        {
            "coordinator": "reviewer",
            "runner": {"argv": [sys.executable, "-c", "pass"]},
            "tasks": [{"task_id": "frontend", "actor": "frontend", "paths": ["src"]}],
        }
    )
    preview = setup_project(root, state, request)
    assert preview["preview_only"] and not state.exists()
    first = setup_project(root, state, request, apply=True)
    assert first["plan_sha256"] == preview["plan_sha256"]
    assert first["registered_tasks"] == ["frontend"]
    assert setup_project(root, state, request, apply=True)["registered_tasks"] == ["frontend"]
    service = Service(state)
    try:
        with service.store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM entities WHERE kind='task'").fetchone()[0] == 1
            assert db.execute("SELECT COUNT(*) FROM retries").fetchone()[0] == 1
        assert not service.context()["decisions"]
        changed = request.model_copy(update={"runner": RunnerConfig(argv=["different"])})
        with pytest.raises(GuardError, match="overwrites"):
            setup_project(root, state, changed, apply=True)
    finally:
        service.close()


def test_next_is_fresh_read_only_and_never_resolves_pending_review(project):
    service, root = project
    validate(service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    with service.store.connect() as db:
        before = dict(db.execute("SELECT key,value FROM meta"))
        count = db.execute("SELECT COUNT(*) FROM entities WHERE kind='receipt'").fetchone()[0]
    assert next_actions(service, ["worker"])["scope_passed"]
    with service.store.connect() as db:
        assert dict(db.execute("SELECT key,value FROM meta")) == before
        assert (
            db.execute("SELECT COUNT(*) FROM entities WHERE kind='receipt'").fetchone()[0] == count
        )
    change = proposal(service)
    result = next_actions(service, ["worker"])
    assert result["findings"][0]["kind"] == "pending_impact"
    assert not result["scope_passed"] and not result["receipt_persisted"]
    accept(service, change, False)
    (root / "code.py").write_text("amount='source changed'\n")
    result = next_actions(service, ["worker"])
    assert "missing_or_stale_evidence" in {f["kind"] for f in result["findings"]}
    assert not gate(service, ["worker"])["receipt"]["passed"]


def test_doctor_catches_missing_task_override_even_with_valid_default(project):
    service, _ = project
    config = service.config.model_copy(
        update={
            "task_runners": {"worker": RunnerConfig(argv=["missing-decisionguard-test-command"])}
        }
    )
    (service.directory / "config.json").write_text(config.model_dump_json())
    # A new CLI/service loads the current configuration.
    current = Service(service.directory)
    try:
        result = doctor(current)
        assert result["runners_available"]["default"]
        assert not result["runners_available"]["task:worker"] and not result["ok"]
    finally:
        current.close()


def test_partial_setup_resumes_without_duplicate_first_task(tmp_path):
    root = tmp_path / "non git"
    root.mkdir()
    state = tmp_path / "state"
    base = {
        "coordinator": "reviewer",
        "runner": {"argv": [sys.executable, "-c", "pass"]},
        "tasks": [
            {"task_id": "one", "actor": "one", "paths": ["one.py"]},
            {
                "task_id": "two",
                "actor": "two",
                "paths": ["two.py"],
                "contracts": [CONTRACT.model_dump()],
            },
        ],
    }
    request = ProjectSetup.model_validate(base)
    with pytest.raises(GuardError):
        setup_project(root, state, request, apply=True)
    local = Service(state)
    try:
        with local.store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM entities WHERE kind='task'").fetchone()[0] == 1
        # The missing dependency is still explicit; setup never silently accepts it.
        with pytest.raises(GuardError):
            setup_project(root, state, request, apply=True)
        with local.store.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM retries").fetchone()[0] == 1
        assert not local.context()["decisions"]
    finally:
        local.close()


def test_setup_rejects_foreign_and_shared_integration_before_initialization(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    other = tmp_path / "foreign"
    other.mkdir()
    state = tmp_path / "state"
    request = ProjectSetup.model_validate(
        {
            "coordinator": "reviewer",
            "runner": {"argv": [sys.executable]},
            "tasks": [{"task_id": "bad", "actor": "bad", "worktree": str(other), "paths": ["."]}],
        }
    )
    with pytest.raises(GuardError, match="worktree root"):
        setup_project(root, state, request, apply=True)
    assert not state.exists()
