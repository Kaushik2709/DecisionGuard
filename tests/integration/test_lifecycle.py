import sqlite3

import pytest
from conftest import CONTRACT, MAJOR, MINOR, accept, key, proposal

from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import AckRequest, MappingRequest, ReviewRequest, TaskMutation
from decisionguard.storage.sqlite import all_entities, heads


def run(service):
    return validate(service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))


def test_pending_rejection_do_not_invalidate(project):
    service, _ = project
    assert run(service)["run"]["passed"]
    assert gate(service, ["worker"])["receipt"]["passed"]
    change = proposal(service)
    with service.store.connect() as db:
        assert all_entities(db, "run")[0]["valid"]
        assert heads(db)[CONTRACT.identity]["version"] == 1
    assert not gate(service, ["worker"])["receipt"]["passed"]
    accept(service, change, False)
    assert gate(service, ["worker"])["receipt"]["passed"]


def test_acceptance_ack_refresh_and_restart(project):
    service, _ = project
    run(service)
    change = proposal(service)
    accepted = accept(service, change)
    assert accepted["revision"] == 2
    with service.store.connect() as db:
        assert not all_entities(db, "run")[0]["valid"]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE versions SET version=99")
    service = Service(service.directory)
    events = service.poll("worker", "worker")["events"]
    assert [
        e["type"] for e in events if e.get("proposal_id") == change["proposal"]["proposal_id"]
    ] == ["pending_impact", "accepted"]
    service.ack(
        AckRequest(
            actor="worker", task_id="worker", idempotency_key=key(), event_id=events[-1]["event_id"]
        )
    )
    assert not gate(service, ["worker"])["receipt"]["passed"]
    service.refresh(TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    kinds = {f["kind"] for f in gate(service, ["worker"])["receipt"]["findings"]}
    assert {"confirmed_conflict", "missing_or_stale_evidence"} <= kinds
    from decisionguard.domain.models import AssumeRequest

    service.assume(
        AssumeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=CONTRACT,
            expected=MINOR,
            observed_version=2,
        )
    )
    run(service)
    assert gate(service, ["worker"])["receipt"]["passed"]
    assert (
        Service(service.directory).poll("worker", "worker")["cursor"]["ack"]
        == events[-1]["event_id"]
    )


def test_idempotency_and_expected_versions(project):
    service, _ = project
    change = proposal(service)
    request = ReviewRequest(
        actor="coordinator",
        idempotency_key="review-once",
        proposal_id=change["proposal"]["proposal_id"],
        accept=True,
        expected_version=1,
        rationale="Review",
    )
    first = service.review(request)
    assert service.review(request) == first
    with pytest.raises(GuardError, match="Retry payload"):
        service.review(request.model_copy(update={"accept": False}))
    with pytest.raises(GuardError, match="Predecessor"):
        proposal(service)


def test_authority_and_delivery(project):
    service, _ = project
    change = proposal(service)
    with pytest.raises(GuardError):
        service.review(
            ReviewRequest(
                actor="worker",
                idempotency_key=key(),
                proposal_id=change["proposal"]["proposal_id"],
                accept=True,
                expected_version=1,
                rationale="Self",
            )
        )
    with pytest.raises(GuardError):
        Service(service.directory, session_actor="worker").review(
            ReviewRequest(
                actor="coordinator",
                idempotency_key=key(),
                proposal_id=change["proposal"]["proposal_id"],
                accept=True,
                expected_version=1,
                rationale="Impersonate",
            )
        )
    with pytest.raises(GuardError):
        service.ack(AckRequest(actor="worker", task_id="worker", idempotency_key=key(), event_id=1))
    with pytest.raises(GuardError):
        service.poll("worker", "someone-else")
    with pytest.raises(GuardError):
        service.poll("worker", "worker", limit=101)
    first = service.poll("worker", "worker", limit=1)["events"]
    assert len(first) == 1
    events = service.poll("worker", "worker", after=first[0]["event_id"])["events"]
    assert events[-1]["type"] == "pending_impact"
    assert service.poll("worker", "worker", after=events[-1]["event_id"])["events"] == []
    accept(service, change)
    assert (
        service.poll("worker", "worker", after=events[-1]["event_id"])["events"][0]["type"]
        == "accepted"
    )


def test_reviewed_same_boundary_compatibility(project):
    service, _ = project
    accept(service, proposal(service))
    service.refresh(TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
    assert any(f["kind"] == "confirmed_conflict" for f in service.conflicts(["worker"])["findings"])
    service.mapping(
        MappingRequest(
            actor="coordinator",
            idempotency_key=key(),
            source=CONTRACT,
            target=CONTRACT,
            source_value=MAJOR,
            target_value=MINOR,
            rationale="Reviewed implementation supports both via adapter",
            evidence=["code.py"],
        )
    )
    assert not service.conflicts(["worker"])["findings"]


def test_tombstone_invalidates_completed_task(project):
    service, _ = project
    run(service)
    accept(service, proposal(service, MINOR.model_copy(update={"deleted": True})))
    kinds = {f["kind"] for f in gate(service, ["worker"])["receipt"]["findings"]}
    assert {"stale_dependencies", "confirmed_conflict", "missing_or_stale_evidence"} <= kinds


def test_losing_stale_proposal_can_be_explicitly_rejected(project):
    service, _ = project
    winner = proposal(service, MINOR)
    loser = proposal(service, MAJOR)
    accept(service, winner)
    rejected = accept(service, loser, False)
    assert rejected["proposal"]["status"] == "rejected"
    assert service.context()["decisions"][CONTRACT.identity]["version"] == 2
    assert not any(f["kind"] == "pending_impact" for f in service.conflicts(["worker"])["findings"])
