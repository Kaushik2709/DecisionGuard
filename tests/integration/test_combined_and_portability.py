import sys

import pytest
from conftest import CONTRACT, MAJOR, key

from decisionguard.application.config import initialize
from decisionguard.application.portability import export_metadata, import_metadata
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.demo import run_demo
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AssumeRequest,
    Mutation,
    RunnerConfig,
    TaskMutation,
    TaskRequest,
)
from decisionguard.git.context import git


def test_required_checkout_demo(tmp_path):
    result = run_demo(tmp_path / "checkout")
    assert result["simulation"]
    assert result["baseline_passed"] and result["pending_notice"]
    assert result["acceptance_invalidated"] and result["acknowledgement_blocked"]
    assert result["clean_merge"] and "499 != 49900" in result["mismatch_output"]
    assert result["repaired_combined_passed"] and result["rejection_adapter_passed"]


def test_actual_combined_files_required(project, tmp_path):
    service, root = project
    combined = tmp_path / "integration"
    git(root, "worktree", "add", "-b", "combined", str(combined))
    service.register(
        TaskRequest(
            actor="integration",
            task_id="integration",
            worktree=str(combined),
            paths=["code.py", "check.py"],
            contracts=[CONTRACT],
            integration=True,
            idempotency_key=key(),
        )
    )
    service.assume(
        AssumeRequest(
            actor="integration",
            task_id="integration",
            idempotency_key=key(),
            contract=CONTRACT,
            expected=MAJOR,
            observed_version=1,
        )
    )
    (root / "code.py").write_text("amount='different-but-valid'\n")
    for identity in ["worker", "integration"]:
        assert validate(
            service, TaskMutation(actor=identity, task_id=identity, idempotency_key=key())
        )["run"]["passed"]
    result = gate(service, ["worker"], "integration")["receipt"]
    assert any(f["kind"] == "combined_source_mismatch" for f in result["findings"])
    (combined / "code.py").write_text((root / "code.py").read_text())
    validate(
        service, TaskMutation(actor="integration", task_id="integration", idempotency_key=key())
    )
    assert gate(service, ["worker"], "integration")["receipt"]["passed"]
    assert not gate(service, ["worker", "integration"])["receipt"]["passed"]


def test_export_import_requires_fresh_local_validation(project, tmp_path):
    service, root = project
    validate(service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    exported = export_metadata(service)
    assert "runs" not in exported and "coordinators" not in exported
    clone = tmp_path / "clone"
    git(tmp_path, "clone", str(root), str(clone))
    state = initialize(clone, None, "coordinator", RunnerConfig(argv=[sys.executable, "check.py"]))
    local = Service(state)
    request = Mutation(actor="coordinator", idempotency_key=key())
    assert import_metadata(local, request, exported)["fresh_validation_required"]
    assert import_metadata(local, request, exported)["imported"]
    local.register(
        TaskRequest(
            actor="worker",
            task_id="worker",
            worktree=str(clone),
            paths=["code.py", "check.py"],
            contracts=[CONTRACT],
            idempotency_key=key(),
        )
    )
    local.assume(
        AssumeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=CONTRACT,
            expected=MAJOR,
            observed_version=1,
        )
    )
    assert not gate(local, ["worker"])["receipt"]["passed"]
    validate(local, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    assert gate(local, ["worker"])["receipt"]["passed"]
    assert local.config.project != service.config.project
    with pytest.raises(GuardError):
        import_metadata(local, Mutation(actor="worker", idempotency_key=key()), exported)


def test_malformed_history_import_is_rejected_without_partial_state(project, tmp_path):
    from copy import deepcopy

    service, root = project
    exported = export_metadata(service)
    clone = tmp_path / "malformed-clone"
    git(tmp_path, "clone", str(root), str(clone))
    state = initialize(clone, None, "coordinator", RunnerConfig(argv=[sys.executable, "check.py"]))
    local = Service(state)
    bad = deepcopy(exported)
    bad["heads"][CONTRACT.identity] = 9
    with pytest.raises(GuardError):
        import_metadata(local, Mutation(actor="coordinator", idempotency_key=key()), bad)
    assert local.context()["decisions"] == {}
    assert import_metadata(local, Mutation(actor="coordinator", idempotency_key=key()), exported)[
        "imported"
    ]
