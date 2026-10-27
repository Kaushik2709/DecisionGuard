from conftest import CONTRACT, accept, key, proposal

from decisionguard.application.services import Service
from decisionguard.domain.models import ScopeApproval, TaskRequest
from decisionguard.storage.sqlite import get


def observer(service, root, paths, task_id="observer"):
    return service.register(
        TaskRequest(
            actor=task_id, task_id=task_id, worktree=str(root), paths=paths, idempotency_key=key()
        )
    )


def test_path_only_observer_gets_pending_and_acceptance(project):
    service, root = project
    observer(service, root, ["check.py"])
    assert CONTRACT.identity in service.context("observer")["decisions"]
    change = proposal(service)
    assert "observer" in change["affected_tasks"]
    assert any(f["kind"] == "pending_impact" for f in service.conflicts(["observer"])["findings"])
    result = accept(service, change)
    assert "observer" in result["affected_tasks"]
    events = Service(service.directory).poll("observer", "observer")["events"]
    assert [
        e["type"] for e in events if e.get("proposal_id") == change["proposal"]["proposal_id"]
    ] == ["pending_impact", "accepted"]
    with service.store.connect() as db:
        assert get(db, "task", "observer")["evidence_generation"] == 1


def test_late_registration_and_expanded_scope_bootstrap_once(project):
    service, root = project
    change = proposal(service)
    observer(service, root, ["unrelated.py"])
    assert not service.poll("observer", "observer")["events"]
    for revision in (0, 1):
        service.approve_scope(
            ScopeApproval(
                actor="coordinator",
                task_id="observer",
                paths=["check.py"],
                expected_scope_revision=revision,
                idempotency_key=key(),
            )
        )
    events = service.poll("observer", "observer")["events"]
    assert len([e for e in events if e["type"] == "accepted_context"]) == 1
    assert (
        len([e for e in events if e.get("proposal_id") == change["proposal"]["proposal_id"]]) == 1
    )
    observer(service, root, ["check.py"], "late")
    assert any(e["type"] == "pending_impact" for e in service.poll("late", "late")["events"])


def test_previous_contract_scope_remains_relevant(project):
    service, root = project
    observer(service, root, ["check.py"])
    service.approve_scope(
        ScopeApproval(
            actor="coordinator",
            task_id="worker",
            paths=["."],
            expected_scope_revision=0,
            idempotency_key=key(),
        )
    )
    from decisionguard.domain.models import ProposeRequest, Value

    request = ProposeRequest(
        actor="worker",
        task_id="worker",
        idempotency_key=key(),
        contract=CONTRACT,
        value=Value(kind="money_unit", value="INR.minor.integer"),
        expected_version=1,
        scope=["new.py"],
        rationale="Move contract scope",
    )
    change = service.propose(request)
    assert "observer" in change["affected_tasks"]
    assert service.propose(request) == change
    assert any(f["kind"] == "pending_impact" for f in service.conflicts(["observer"])["findings"])
    assert "observer" in accept(service, change)["affected_tasks"]


def test_impact_reports_metadata_staleness_without_claiming_source_freshness(project):
    from decisionguard.application.validation import validate
    from decisionguard.domain.models import TaskMutation

    service, root = project
    validate(service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    before = service.impact(["worker"])
    assert not before["source_freshness_checked"] and not before["receipt_created"]
    assert not before["tasks"]["worker"]["validation_required"]
    (root / "code.py").write_text("amount = 49900\n")
    assert (
        service.impact(["worker"])["tasks"]["worker"]["source_freshness"] == "requires_gate_check"
    )
    service.refresh(TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    assert service.impact(["worker"])["tasks"]["worker"]["validation_required"]
