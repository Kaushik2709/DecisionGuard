"""Positive and negative controls for what declared evidence can actually establish."""

import json
from decimal import Decimal

from conftest import CONTRACT, MAJOR, MINOR, accept, key

from decisionguard.application.validation import gate, validate
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    MappingRequest,
    ProposeRequest,
    TaskMutation,
)


def run(service):
    return validate(service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))


def test_reviewed_conversion_cannot_override_broken_implementation(project, tmp_path):
    service, root = project
    provider = Contract(boundary="provider.request", key="amount.unit")
    code = (
        "from decimal import Decimal\n"
        "amount = '499.00'\n"
        "def to_provider(value):\n"
        "    return int(Decimal(value) * 100)\n"
    )
    (root / "code.py").write_text(code, encoding="utf-8")
    (root / "check.py").write_text(
        "from code import amount, to_provider\nassert to_provider(amount) == 49900\n",
        encoding="utf-8",
    )
    change = service.propose(
        ProposeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=provider,
            value=MINOR,
            expected_version=0,
            scope=["code.py", "check.py"],
            rationale="Explicit provider minor-unit boundary",
        )
    )
    accept(service, change)
    service.assume(
        AssumeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=provider,
            expected=MINOR,
            observed_version=1,
        )
    )
    service.mapping(
        MappingRequest(
            actor="coordinator",
            idempotency_key=key(),
            source=CONTRACT,
            target=provider,
            source_value=MAJOR,
            target_value=MINOR,
            rationale="Reviewed major-to-minor adapter",
            evidence=["code.py", "check.py"],
        )
    )
    before = run(service)
    assert before["run"]["passed"]
    assert gate(service, ["worker"])["receipt"]["passed"]

    (root / "code.py").write_text(code.replace(" * 100", ""), encoding="utf-8")
    stale = gate(service, ["worker"])
    assert not stale["receipt"]["passed"]
    failed = run(service)
    assert failed["run"]["valid"] and not failed["run"]["passed"]
    assert "AssertionError" in failed["run"]["output"]
    blocked = gate(service, ["worker"])
    assert not blocked["receipt"]["passed"]
    assert any(f["kind"] == "missing_or_stale_evidence" for f in blocked["receipt"]["findings"])

    (root / "code.py").write_text(code, encoding="utf-8")
    repaired = run(service)
    assert repaired["run"]["passed"]
    final = gate(service, ["worker"])
    assert final["receipt"]["passed"]
    (tmp_path / "conversion-case.json").write_text(
        json.dumps(
            {
                "fixture_only": True,
                "initial": before,
                "stale_gate": stale,
                "broken_adapter": failed,
                "blocked_gate": blocked,
                "repaired": repaired,
                "repaired_gate": final,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_undeclared_unit_bug_can_escape_a_weak_configured_check(project, tmp_path):
    service, root = project
    # The declared contract and assumption both remain major units. The implementation
    # silently sends a minor-unit value; the configured check only asserts nonemptiness.
    amount = "49900"
    (root / "code.py").write_text(f"amount = {amount!r}\n", encoding="utf-8")
    observation = run(service)
    receipt = gate(service, ["worker"])
    actual_provider_amount = int(Decimal(amount) * 100)
    assert actual_provider_amount == 4_990_000 and actual_provider_amount != 49_900
    assert observation["run"]["passed"] and receipt["receipt"]["passed"]
    # This deliberately passing gate is a known coverage limit, not a successful
    # detection: current evidence proves only the operator's weak configured check.
    (tmp_path / "undeclared-negative-control.json").write_text(
        json.dumps(
            {
                "fixture_only": True,
                "known_limit_confirmed": True,
                "actual_provider_amount": actual_provider_amount,
                "business_expected": 49_900,
                "configured_test": "assert amount (nonempty only)",
                "validation": observation,
                "gate": receipt,
                "interpretation": "Undeclared business semantics outside configured assertions can escape",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
