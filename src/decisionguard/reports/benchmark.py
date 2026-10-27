import multiprocessing
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from decisionguard.application.config import initialize
from decisionguard.application.services import Service, envelope
from decisionguard.application.validation import gate, validate
from decisionguard.demo import MAJOR, MINOR, PUBLIC, SCOPES, key, run_demo
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    MappingRequest,
    ProposeRequest,
    ReviewRequest,
    RunnerConfig,
    TaskMutation,
    TaskRequest,
    Value,
)
from decisionguard.git.context import common_dir, git

# Planted, manually labeled diagnostic fixtures; not sampled production workloads.
# name, kind, expected, actual, relationship, label
CASES = [
    ("money", "money_unit", "INR.major.decimal-string", "INR.minor.integer", "same", "conflict"),
    ("time", "time_unit", "seconds", "milliseconds", "same", "conflict"),
    ("authentication", "auth", "required", "optional", "same", "conflict"),
    ("response envelope", "schema", "sha256:envelope-v1", "sha256:envelope-v2", "same", "unknown"),
    ("idempotency", "idempotency", "required", "optional", "same", "conflict"),
    ("error format", "error_format", "problem-json", "custom-json", "same", "conflict"),
    ("retry policy", "retry_policy", "bounded", "none", "same", "conflict"),
    (
        "compatible conversion",
        "money_unit",
        "INR.major.decimal-string",
        "INR.minor.integer",
        "adapter",
        "clear",
    ),
    ("identical money", "money_unit", "INR.minor.integer", "INR.minor.integer", "same", "clear"),
    ("identical auth", "auth", "required", "required", "same", "clear"),
    ("independent contracts", "time_unit", "seconds", "milliseconds", "independent", "clear"),
    ("identical schema", "schema", "sha256:a", "sha256:a", "same", "clear"),
    ("free text", "text", "append only", "mutable", "same", "unknown"),
    ("schema reviewed compatible", "schema", "sha256:a", "sha256:b", "reviewed", "clear"),
    (
        "currency mismatch",
        "money_unit",
        "USD.minor.integer",
        "EUR.minor.integer",
        "same",
        "conflict",
    ),
    (
        "representation mismatch",
        "money_unit",
        "INR.major.decimal-string",
        "INR.major.float",
        "same",
        "conflict",
    ),
    ("microseconds mismatch", "time_unit", "milliseconds", "microseconds", "same", "conflict"),
    ("expiry mismatch", "time_unit", "seconds", "minutes", "same", "conflict"),
    ("auth mechanism", "auth", "bearer", "cookie", "same", "conflict"),
    ("auth audience", "auth", "checkout", "admin", "same", "conflict"),
    ("retry limit", "retry_policy", "three_attempts", "unbounded", "same", "conflict"),
    ("retry backoff", "retry_policy", "exponential", "immediate", "same", "conflict"),
    ("idempotency scope", "idempotency", "per_order", "per_request", "same", "conflict"),
    ("error fields", "error_format", "problem-json", "plain-text", "same", "conflict"),
    ("same time", "time_unit", "seconds", "seconds", "same", "clear"),
    ("same retry", "retry_policy", "bounded", "bounded", "same", "clear"),
    ("same idempotency", "idempotency", "required", "required", "same", "clear"),
    ("same error", "error_format", "problem-json", "problem-json", "same", "clear"),
    ("same dollar", "money_unit", "USD.minor.integer", "USD.minor.integer", "same", "clear"),
    ("same architecture text", "text", "append only", "append only", "same", "clear"),
    ("unreviewed schema", "schema", "sha256:c", "sha256:d", "same", "unknown"),
    ("unknown pagination schema", "schema", "sha256:page1", "sha256:page2", "same", "unknown"),
    (
        "unknown migration prose",
        "text",
        "eventual migration",
        "atomic migration",
        "same",
        "unknown",
    ),
    ("unknown architecture prose", "text", "cache locally", "cache remotely", "same", "unknown"),
]


def exercise_case(kind: str, expected: str, actual: str, relationship: str) -> dict[str, Any]:
    """Every prediction comes from real services, reviewed metadata and local runner evidence."""
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="benchmark-service-", dir=artifacts) as directory:
        root = Path(directory).resolve()
        git(root, "init", "-b", "main")
        script = (
            "from decimal import Decimal\nassert int(Decimal('499.00') * 100) == 49900\n"
            if relationship == "adapter"
            else "assert True\n"
        )
        (root / "check.py").write_text(script, encoding="utf-8")
        service = Service(
            initialize(root, None, "reviewer", RunnerConfig(argv=[sys.executable, "check.py"]))
        )
        contract = Contract(boundary="public", key="contract")
        other = Contract(boundary="provider", key="contract")
        before = Value.model_validate({"kind": kind, "value": expected})
        after = Value.model_validate({"kind": kind, "value": actual})
        service.register(
            TaskRequest(
                actor="worker",
                task_id="worker",
                paths=["check.py"],
                worktree=str(root),
                idempotency_key=key(),
            )
        )

        def publish(target: Contract, value: Value, version: int) -> None:
            item = service.propose(
                ProposeRequest(
                    actor="worker",
                    task_id="worker",
                    idempotency_key=key(),
                    contract=target,
                    value=value,
                    expected_version=version,
                    scope=["check.py"],
                    rationale="Labeled benchmark fixture",
                )
            )["proposal"]
            service.review(
                ReviewRequest(
                    actor="reviewer",
                    idempotency_key=key(),
                    proposal_id=item["proposal_id"],
                    expected_version=version,
                    accept=True,
                    rationale="Explicit fixture review",
                )
            )

        publish(contract, before, 0)
        service.assume(
            AssumeRequest(
                actor="worker",
                task_id="worker",
                idempotency_key=key(),
                contract=contract,
                expected=before,
                observed_version=1,
            )
        )
        if relationship in {"adapter", "independent"}:
            publish(other, after, 0)
            service.assume(
                AssumeRequest(
                    actor="worker",
                    task_id="worker",
                    idempotency_key=key(),
                    contract=other,
                    expected=after,
                    observed_version=1,
                )
            )
        else:
            publish(contract, after, 1)
        if relationship in {"adapter", "reviewed"}:
            service.mapping(
                MappingRequest(
                    actor="reviewer",
                    idempotency_key=key(),
                    source=contract,
                    target=other if relationship == "adapter" else contract,
                    source_value=before,
                    target_value=after,
                    rationale="Reviewed fixture conversion",
                    evidence=["check.py"],
                )
            )
        service.refresh(TaskMutation(actor="worker", task_id="worker", idempotency_key=key()))
        run = validate(
            service, TaskMutation(actor="worker", task_id="worker", idempotency_key=key())
        )["run"]
        receipt = gate(service, ["worker"])["receipt"]
        kinds = {f["kind"] for f in receipt["findings"]}
        prediction = (
            "clear"
            if receipt["passed"]
            else "conflict"
            if "confirmed_conflict" in kinds
            else "unknown"
            if "unknown_compatibility" in kinds
            else "blocked"
        )
        service.close()
        return {
            "predicted": prediction,
            "gate_passed": receipt["passed"],
            "runner_passed": run["passed"],
            "findings": sorted(kinds),
        }


def compete_review(args: tuple[str, str]) -> str:
    directory, proposal_id = args
    try:
        Service(Path(directory)).review(
            ReviewRequest(
                actor="coordinator",
                idempotency_key=key(),
                proposal_id=proposal_id,
                accept=True,
                expected_version=2,
                rationale="Concurrent fixture review",
            )
        )
        return "accepted"
    except GuardError as exc:
        return exc.code


def evaluate() -> dict[str, Any]:
    started = time.perf_counter()
    rows = []
    for name, kind, expected, actual, relationship, label in CASES:
        outcome = exercise_case(kind, expected, actual, relationship)
        rows.append({"name": name, "label": label, "relationship": relationship, **outcome})
    tp = sum(r["label"] == r["predicted"] == "conflict" for r in rows)
    fp = sum(r["predicted"] == "conflict" and r["label"] != "conflict" for r in rows)
    fn = sum(r["label"] == "conflict" and r["predicted"] != "conflict" for r in rows)
    demo = run_demo()
    common = common_dir(Path(demo["directory"]) / "repository with spaces")
    assert common is not None
    service = Service(common / "decisionguard")
    proposals = [
        service.propose(
            ProposeRequest(
                actor="backend",
                task_id="backend-contract",
                idempotency_key=key(),
                contract=PUBLIC,
                value=value,
                expected_version=2,
                scope=SCOPES,
                rationale="Competing benchmark proposal",
            )
        )["proposal"]["proposal_id"]
        for value in [MAJOR, MINOR]
    ]
    with ProcessPoolExecutor(
        max_workers=2, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        outcomes = list(pool.map(compete_review, [(str(service.directory), p) for p in proposals]))
    lifecycle = {
        name: demo[name]
        for name in [
            "pending_notice",
            "pending_blocked",
            "acceptance_invalidated",
            "acknowledgement_blocked",
            "repaired_combined_passed",
            "rejection_adapter_passed",
        ]
    }
    lifecycle["concurrent_changes_single_winner"] = sorted(outcomes) == [
        "VERSION_CONFLICT",
        "accepted",
    ]
    return envelope(
        fixture_only=True,
        scenarios=rows,
        classification_count=len(rows),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=tp / (tp + fp) if tp + fp else None,
        precision_denominator=tp + fp,
        recall=tp / (tp + fn) if tp + fn else None,
        recall_denominator=tp + fn,
        unknown_count=sum(r["predicted"] == "unknown" for r in rows),
        correctly_classified=sum(r["label"] == r["predicted"] for r in rows),
        lifecycle=lifecycle,
        lifecycle_count=len(lifecycle),
        lifecycle_passed=sum(lifecycle.values()),
        runtime_seconds=round(time.perf_counter() - started, 4),
    )
