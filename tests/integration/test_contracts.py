import json

import pytest
from conftest import key

from decisionguard.application.contracts import publish, scan
from decisionguard.application.services import Service
from decisionguard.application.validation import gate
from decisionguard.domain.contracts import ContractPublish, ContractScan, OperationBinding
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    ReviewRequest,
    ScopeApproval,
    Value,
)
from decisionguard.domain.schemas import compare_artifacts


def document(schema, direction="response"):
    container = {"content": {"application/json": {"schema": schema}}}
    operation = (
        {"responses": {"200": container}} if direction == "response" else {"requestBody": container}
    )
    return {"openapi": "3.1.1", "paths": {"/checkout": {"post": operation}}}


def setup(service, root, schema, direction="response"):
    service.approve_scope(
        ScopeApproval(
            actor="coordinator",
            task_id="worker",
            paths=["."],
            expected_scope_revision=0,
            idempotency_key=key(),
        )
    )
    (root / "openapi.json").write_text(json.dumps(document(schema, direction)))
    binding = OperationBinding(
        method="post",
        path="/checkout",
        direction=direction,
        contract=Contract(boundary="checkout", key=direction),
        scope=["."],
    )
    return ContractScan(task_id="worker", spec="openapi.json", bindings=[binding])


def accept_preview(service, request):
    preview = scan(service, request)
    versions = service.context()["decisions"]
    keys = [f"{p['contract']['boundary']}::{p['contract']['key']}" for p in preview["proposals"]]
    submission = ContractPublish(
        actor="worker",
        idempotency_key=key(),
        scan=request,
        preview_digest=preview["preview_digest"],
        expected_versions={k: versions.get(k, {}).get("version", 0) for k in keys},
        rationale="Review API fixture",
    )
    batch = publish(service, submission)
    for result in batch["proposals"]:
        proposal = result["proposal"]
        service.review(
            ReviewRequest(
                actor="coordinator",
                idempotency_key=key(),
                proposal_id=proposal["proposal_id"],
                accept=True,
                expected_version=proposal["expected_version"],
                rationale="Reviewed API",
            )
        )
    assert publish(service, submission) == batch  # Retry after review does not republish.
    return preview


def test_real_schema_change_reaches_gate_with_pointer_and_stale_evidence(project):
    service, root = project
    before = {
        "type": "object",
        "required": ["amount"],
        "properties": {"amount": {"type": "integer"}},
        "additionalProperties": False,
    }
    request = setup(service, root, before)
    first = accept_preview(service, request)
    service.assume(
        AssumeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=request.bindings[0].contract,
            expected=Value.model_validate(first["proposals"][0]["value"]),
            observed_version=1,
        )
    )
    (root / "openapi.json").write_text(
        json.dumps(document({**before, "properties": {"amount": {"type": "string"}}}))
    )
    second = accept_preview(service, request)
    assert second["proposals"][0]["comparison"] == "incompatible"
    problems = service.conflicts(["worker"])["findings"]
    assert any(
        p["kind"] == "confirmed_conflict"
        and any("amount" in e["pointer"] for e in p.get("details", []))
        for p in problems
    )
    assert not gate(service, ["worker"])["receipt"]["passed"]


@pytest.mark.parametrize(
    "direction,left,right,expected",
    [
        ("request", {"type": "integer"}, {"type": "number"}, "equal"),
        ("response", {"type": "integer"}, {"type": "number"}, "incompatible"),
        ("response", {"type": "number"}, {"type": "integer"}, "equal"),
        ("request", {"type": "string"}, {"type": "string", "enum": ["paid"]}, "incompatible"),
        ("response", {"type": "string", "enum": ["paid"]}, {"type": "string"}, "incompatible"),
        ("response", {"type": "string"}, {"type": ["string", "null"]}, "incompatible"),
        ("request", {"type": "string"}, {"type": ["string", "null"]}, "equal"),
        (
            "response",
            {"type": "string", "pattern": "x"},
            {"type": "string", "pattern": "x"},
            "unknown",
        ),
        (
            "response",
            {"type": "array", "items": {"type": "string"}},
            {"type": "array", "items": {"type": "integer"}},
            "incompatible",
        ),
    ],
)
def test_directional_schema_cases(direction, left, right, expected):
    def artifact(schema):
        return {"direction": direction, "schema": schema}

    assert compare_artifacts(artifact(left), artifact(right))[0] == expected


def test_preview_is_read_only_and_publication_is_atomic_and_source_bound(project):
    service, root = project
    request = setup(service, root, {"type": "integer"})
    preview = scan(service, request)
    submission = ContractPublish(
        actor="worker",
        idempotency_key=key(),
        scan=request,
        preview_digest=preview["preview_digest"],
        expected_versions={},
        rationale="Missing version",
    )
    with pytest.raises(GuardError):
        publish(service, submission)
    with service.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
    (root / "openapi.json").write_text(json.dumps(document({"type": "number"})))
    with pytest.raises(GuardError) as error:
        publish(service, submission)
    assert error.value.code == "SOURCE_CHANGED"


def test_mcp_preview_rejects_foreign_scope_and_external_refs_are_unknown(project):
    service, root = project
    request = setup(service, root, {"$ref": "https://example.invalid/never-fetch"})
    assert scan(service, request)["proposals"][0]["artifact"]["unsupported"]
    fixed = Service(service.directory, session_actor="other")
    with pytest.raises(GuardError):
        scan(fixed, request)


def test_batch_failure_rolls_back_earlier_proposals_and_artifacts(project):
    service, root = project
    request = setup(service, root, {"type": "integer"})
    original = request.bindings[0]
    request = request.model_copy(
        update={
            "bindings": [
                original,
                original.model_copy(
                    update={"contract": Contract(boundary="checkout", key="second")}
                ),
            ]
        }
    )
    preview = scan(service, request)
    submission = ContractPublish(
        actor="worker",
        idempotency_key=key(),
        scan=request,
        preview_digest=preview["preview_digest"],
        expected_versions={"checkout::response": 0, "checkout::second": 999},
        rationale="Atomic failure fixture",
    )
    with pytest.raises(GuardError):
        publish(service, submission)
    with service.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 0
        assert (
            db.execute(
                "SELECT COUNT(*) FROM entities WHERE kind='proposal' AND json_extract(body,'$.status')='pending'"
            ).fetchone()[0]
            == 0
        )


def test_root_security_inheritance_and_unresolved_path_are_explicit(project):
    service, root = project
    request = setup(service, root, {"type": "integer"})
    auth = request.model_copy(
        update={"bindings": [request.bindings[0].model_copy(update={"direction": "security"})]}
    )
    spec = document({"type": "integer"})
    spec["security"] = [{"bearer": []}]
    spec["components"] = {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}}
    (root / "openapi.json").write_text(json.dumps(spec))
    before = scan(service, auth)["proposals"][0]["artifact"]
    spec["paths"]["/checkout"]["post"]["security"] = []
    (root / "openapi.json").write_text(json.dumps(spec))
    after = scan(service, auth)["proposals"][0]["artifact"]
    assert compare_artifacts(before, after)[0] == "incompatible"
    spec["paths"]["/checkout"] = {"$ref": "https://example.invalid/never-fetch"}
    (root / "openapi.json").write_text(json.dumps(spec))
    item = scan(service, request)["proposals"][0]
    assert item["artifact"]["unsupported"] and not item["value"]["deleted"]


def test_reference_expansion_is_bounded_before_serialization(project):
    service, root = project
    request = setup(service, root, {"type": "string", "description": "x" * 140000})
    with pytest.raises(GuardError) as error:
        scan(service, request)
    assert error.value.code == "RESOURCE_LIMIT"


def test_v2_artifacts_transfer_without_runner_authority_or_evidence(project, tmp_path):
    import sys

    from decisionguard.application.config import initialize
    from decisionguard.application.portability import export_metadata, import_metadata
    from decisionguard.domain.models import Mutation, RunnerConfig
    from decisionguard.git.context import git

    service, root = project
    request = setup(service, root, {"type": "integer"})
    accept_preview(service, request)
    metadata = export_metadata(service)
    assert metadata["schema_version"] == 2 and metadata["artifacts"]
    clone = tmp_path / "clone"
    git(tmp_path, "clone", str(root), str(clone))
    other = Service(
        initialize(clone, None, "coordinator", RunnerConfig(argv=[sys.executable, "check.py"]))
    )
    assert import_metadata(other, Mutation(actor="coordinator", idempotency_key=key()), metadata)[
        "fresh_validation_required"
    ]
    with other.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM entities WHERE kind='run'").fetchone()[0] == 0
