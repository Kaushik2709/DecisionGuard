import json
import sys

import pytest
from conftest import CONTRACT, MAJOR, key

from decisionguard.application.config import initialize
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    ProposeRequest,
    ResourceLimits,
    RunnerConfig,
    ScopeApproval,
    TaskMutation,
    TaskRequest,
)
from decisionguard.git.context import git


@pytest.mark.parametrize("change", ["dirty", "committed", "untracked", "renamed", "deleted"])
def test_out_of_scope_changes_block_even_with_passing_runner(project, change):
    service, root = project
    config = service.config.model_copy(
        update={"runner": RunnerConfig(argv=[sys.executable, "-c", "pass"])}
    )
    (service.directory / "config.json").write_text(config.model_dump_json())
    service.approve_scope(
        ScopeApproval(
            actor="coordinator",
            task_id="worker",
            paths=["check.py"],
            expected_scope_revision=0,
            idempotency_key=key(),
        )
    )
    if change in {"dirty", "committed"}:
        (root / "code.py").write_text("amount = 'changed'\n")
        if change == "committed":
            git(root, "add", ".")
            git(
                root,
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-m",
                "Change",
            )
    elif change == "untracked":
        (root / "new.py").write_text("extra = True\n")
    elif change == "renamed":
        (root / "code.py").rename(root / "renamed.py")
        git(root, "add", ".")
    else:
        (root / "code.py").unlink()
    result = validate(
        service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key())
    )
    assert result["run"]["passed"]
    receipt = gate(service, ["worker"])["receipt"]
    assert not receipt["passed"]
    assert any(f["kind"] == "out_of_scope_change" for f in receipt["findings"])


def test_quotas_do_not_break_idempotent_retries(project):
    service, root = project
    config = service.config.model_copy(
        update={"limits": ResourceLimits(pending_per_actor=1, tasks_per_project=2)}
    )
    (service.directory / "config.json").write_text(config.model_dump_json())
    request = ProposeRequest(
        actor="worker",
        task_id="worker",
        contract=CONTRACT,
        value=MAJOR,
        expected_version=1,
        scope=["code.py"],
        rationale="Quota test",
        idempotency_key=key(),
    )
    assert service.propose(request) == service.propose(request)
    with pytest.raises(GuardError) as error:
        service.propose(request.model_copy(update={"idempotency_key": key()}))
    assert error.value.code == "RESOURCE_LIMIT"
    task = TaskRequest(
        actor="worker",
        task_id="extra",
        worktree=str(root),
        paths=["code.py"],
        idempotency_key=key(),
    )
    assert service.register(task) == service.register(task)
    with pytest.raises(GuardError) as error:
        service.register(task.model_copy(update={"task_id": "overflow", "idempotency_key": key()}))
    assert error.value.code == "RESOURCE_LIMIT"


@pytest.mark.parametrize("boundary", ["journal", "database", "publication"])
def test_init_failure_boundaries_recover_same_identity(tmp_path, monkeypatch, boundary):
    import decisionguard.application.config as module

    root = tmp_path / "project"
    root.mkdir()
    state = root / "state"
    runner = RunnerConfig(argv=[sys.executable, "-c", "pass"])
    original_write = module.atomic_json
    original_store = module.Store

    def fail_write(path, content):
        if boundary == "publication" and path.name == "config.json":
            raise OSError("Injected publication failure")
        original_write(path, content)
        if boundary == "journal" and path.name == "initialization.json":
            raise OSError("Injected journal failure")

    def fail_store(*args, **kwargs):
        result = original_store(*args, **kwargs)
        if boundary == "database":
            raise OSError("Injected database boundary failure")
        return result

    with monkeypatch.context() as local:
        local.setattr(module, "atomic_json", fail_write)
        local.setattr(module, "Store", fail_store)
        with pytest.raises(OSError, match="Injected"):
            initialize(root, state, "coordinator", runner)
    intended = json.loads((state / "initialization.json").read_text())["project"]
    assert initialize(root, state, "coordinator", runner) == state
    assert Service(state).config.project == intended
