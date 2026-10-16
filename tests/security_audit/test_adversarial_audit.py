"""Regression tests: the seven original audit reproductions must now fail safely."""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from conftest import CONTRACT, MAJOR, key, proposal

from decisionguard.application.config import initialize
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    ProposeRequest,
    ReviewRequest,
    RunnerConfig,
    TaskMutation,
    TaskRequest,
)
from decisionguard.git.context import git


def run(service, actor="worker"):
    return validate(service, TaskMutation(actor=actor, task_id=actor, idempotency_key=key()))


def register(service, root, identity, paths, integration=False):
    service.register(
        TaskRequest(
            actor=identity,
            task_id=identity,
            worktree=str(root),
            paths=paths,
            contracts=[CONTRACT],
            integration=integration,
            idempotency_key=key(),
        )
    )
    service.assume(
        AssumeRequest(
            actor=identity,
            task_id=identity,
            contract=CONTRACT,
            expected=MAJOR,
            observed_version=1,
            idempotency_key=key(),
        )
    )


def test_audit_01_changed_code_omitted_from_combined_source(project, tmp_path):
    service, root = project
    combined = tmp_path / "combined"
    git(root, "worktree", "add", "-b", "audit-combined", str(combined))
    register(service, root, "narrow", ["check.py"])
    register(service, combined, "integration", ["code.py", "check.py"], True)
    (root / "code.py").write_text("amount = '999.00'\n")
    assert (combined / "code.py").read_text() != (root / "code.py").read_text()
    assert run(service, "narrow")["run"]["passed"]
    assert run(service, "integration")["run"]["passed"]
    receipt = gate(service, ["narrow"], "integration")["receipt"]
    assert not receipt["passed"]
    assert any(f["kind"] == "out_of_scope_change" for f in receipt["findings"])


def test_audit_02_same_worktree_can_supply_both_sides_of_integration(project, tmp_path):
    service, root = project
    combined = tmp_path / "shared"
    git(root, "worktree", "add", "-b", "audit-shared", str(combined))
    register(service, combined, "selected", ["code.py", "check.py"])
    register(service, combined, "integration", ["code.py", "check.py"], True)
    assert run(service, "selected")["run"]["passed"]
    assert run(service, "integration")["run"]["passed"]
    with pytest.raises(GuardError, match="distinct worktree"):
        gate(service, ["selected"], "integration")
    with pytest.raises(GuardError, match="distinct task"):
        gate(service, ["integration"], "integration")


def test_audit_03_finished_run_overwrites_concurrent_refresh_invalidation(project, monkeypatch):
    service, _ = project
    import decisionguard.application.validation as module

    original = module.execute
    completed = threading.Event()
    resume = threading.Event()

    def paused_execute(root, config):
        outcome = original(root, config)
        completed.set()
        assert resume.wait(15)
        return outcome

    monkeypatch.setattr(module, "execute", paused_execute)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run, service)
        try:
            assert completed.wait(15)
            service.refresh(TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
        finally:
            resume.set()
        result = future.result(timeout=20)
    assert not result["run"]["valid"]
    assert not gate(service, ["worker"])["receipt"]["passed"]
    assert run(service)["run"]["valid"]
    assert gate(service, ["worker"])["receipt"]["passed"]


def test_audit_04_removed_coordinator_retains_running_session_authority(project):
    service, _ = project
    pending = proposal(service)
    bound = Service(service.directory, session_actor="coordinator")
    config = service.config.model_copy(update={"coordinators": ["replacement"]})
    (service.directory / "config.json").write_text(config.model_dump_json())
    request = ReviewRequest(
        actor="coordinator",
        proposal_id=pending["proposal"]["proposal_id"],
        accept=True,
        expected_version=1,
        rationale="Audit: revoked identity still accepted",
        idempotency_key=key(),
    )
    with pytest.raises(GuardError, match="Coordinator"):
        bound.review(request)
    assert "coordinator" not in Service(service.directory).config.coordinators


def test_audit_05_new_failed_run_does_not_supersede_old_success(project, tmp_path):
    service, _ = project
    sentinel = tmp_path / "external-service-down"
    runner = RunnerConfig(
        argv=[
            sys.executable,
            "-c",
            "import pathlib,sys;sys.exit(pathlib.Path(sys.argv[1]).exists())",
            str(sentinel),
        ]
    )
    config = service.config.model_copy(update={"runner": runner})
    (service.directory / "config.json").write_text(config.model_dump_json())
    service = Service(service.directory)
    assert run(service)["run"]["passed"]
    sentinel.write_text("deterministic external failure")
    failed = run(service)["run"]
    assert failed["exit_code"] == 1 and not failed["passed"]
    assert not gate(service, ["worker"])["receipt"]["passed"]
    sentinel.unlink()
    assert run(service)["run"]["passed"]
    assert gate(service, ["worker"])["receipt"]["passed"]


def test_audit_06_any_worker_can_block_unrelated_task_scope(project):
    service, root = project
    register(service, root, "outsider", ["check.py"])
    bound = Service(service.directory, session_actor="outsider")
    request = ProposeRequest(
        actor="outsider",
        task_id="outsider",
        idempotency_key=key(),
        contract=Contract(boundary="unrelated", key="new"),
        value=MAJOR,
        expected_version=0,
        scope=["."],
        rationale="Audit broad pending impact",
    )
    with pytest.raises(GuardError, match="approved task scope"):
        bound.propose(request)
    assert service.conflicts(["worker"])["findings"] == []


def test_audit_07_interrupted_initialization_cannot_be_retried(tmp_path, monkeypatch):
    root = tmp_path / "non-git-project"
    root.mkdir()
    state = root / "state"
    runner = RunnerConfig(argv=[sys.executable, "-c", "pass"])
    original = Path.open

    def fail_config(self, *args, **kwargs):
        if self == state / "config.json.tmp":
            raise OSError("Audit simulated failure between DB and config creation")
        return original(self, *args, **kwargs)

    with monkeypatch.context() as local:
        local.setattr(Path, "open", fail_config)
        with pytest.raises(OSError, match="Audit simulated"):
            initialize(root, state, "coordinator", runner)
    assert (state / "state.db").is_file() and not (state / "config.json").exists()
    assert initialize(root, state, "coordinator", runner) == state
    assert Service(state).context()["decisions"] == {}
