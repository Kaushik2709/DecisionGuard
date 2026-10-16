import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from decisionguard.application.services import Service, envelope
from decisionguard.demo import MAJOR, MINOR, PUBLIC, SCOPES, key, run_demo
from decisionguard.domain.compatibility import compare
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import ProposeRequest, ReviewRequest, Value
from decisionguard.git.context import common_dir

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
]


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
        raw = compare(
            Value.model_validate({"kind": kind, "value": expected}),
            Value.model_validate({"kind": kind, "value": actual}),
        )
        predicted = (
            "clear"
            if relationship in {"independent", "adapter", "reviewed"}
            else {"equal": "clear", "incompatible": "conflict", "unknown": "unknown"}[raw]
        )
        rows.append(
            {"name": name, "label": label, "predicted": predicted, "relationship": relationship}
        )
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
