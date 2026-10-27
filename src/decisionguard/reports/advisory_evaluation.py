"""Evaluate operator-labelled cases against stored responses without making model calls."""

import json
import math
from typing import Any, Literal

from pydantic import Field

from decisionguard.application.services import Service, envelope
from decisionguard.domain.errors import require
from decisionguard.domain.models import Model

Label = Literal["possible_contract_impact", "no_impact_indicated", "insufficient_context"]


class EvaluationCase(Model):
    id: str = Field(min_length=1, max_length=200)
    repository: str = Field(min_length=1, max_length=200)
    change_family: str = Field(min_length=1, max_length=200)
    split: Literal["development", "heldout"]
    expected: Label
    reviewed_by: str = Field(min_length=1, max_length=200)
    advisory_id: str = Field(min_length=64, max_length=64)
    candidate: str = Field(default="candidate_0", pattern=r"^candidate_[0-4]$")
    deterministic_prediction: Label
    heuristic_prediction: Label


class EvaluationDataset(Model):
    schema_version: Literal[1]
    fixture_only: bool
    cases: list[EvaluationCase] = Field(min_length=1, max_length=10000)


def evaluate(service: Service, dataset: EvaluationDataset) -> dict[str, Any]:
    require(service.session_actor is None, "FORBIDDEN", "Evaluation is a local operator operation")
    require(
        len({c.id for c in dataset.cases}) == len(dataset.cases), "INVALID", "Duplicate case ID"
    )
    require(
        len({(c.advisory_id, c.candidate) for c in dataset.cases}) == len(dataset.cases),
        "INVALID",
        "Duplicate prediction cannot count as another evaluation example",
    )
    for field in ("repository", "change_family"):
        left = {getattr(c, field) for c in dataset.cases if c.split == "development"}
        right = {getattr(c, field) for c in dataset.cases if c.split == "heldout"}
        require(not left & right, "INVALID", "Development/held-out grouping leakage")
    rows, models = [], set()
    successful_latencies: dict[str, float] = {}
    with service.store.connect() as db:
        for case in dataset.cases:
            row = db.execute(
                "SELECT body FROM advisory_runs WHERE id=?", (case.advisory_id,)
            ).fetchone()
            require(
                row is not None, "NOT_FOUND", "Evaluation references an unknown stored advisory"
            )
            record = json.loads(row[0])
            if (
                case.split == "heldout"
                and record["status"] == "available"
                and isinstance(record.get("provider_latency_ms"), (float, int))
            ):
                successful_latencies[case.advisory_id] = record["provider_latency_ms"]
            models.add(record["model"])
            predicted = (
                record.get("answers", {}).get(case.candidate, {}).get("label")
                if record["status"] == "available"
                else None
            )
            rows.append(
                {
                    "id": case.id,
                    "split": case.split,
                    "expected": case.expected,
                    "jev": predicted,
                    "deterministic": case.deterministic_prediction,
                    "heuristic": case.heuristic_prediction,
                    "advisory_status": record["status"],
                }
            )
    require(len(models) == 1, "INVALID", "Evaluate one pinned model version at a time")
    heldout = [r for r in rows if r["split"] == "heldout"]
    metrics = {}
    for method in ("deterministic", "heuristic", "jev"):
        positive = "possible_contract_impact"
        tp = sum(r[method] == r["expected"] == positive for r in heldout)
        fp = sum(r[method] == positive and r["expected"] != positive for r in heldout)
        fn = sum(r["expected"] == positive and r[method] != positive for r in heldout)
        benign = [r for r in heldout if r["expected"] == "no_impact_indicated"]
        metrics[method] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "abstentions": sum(
                r[method] is None or r[method] == "insufficient_context" for r in heldout
            ),
            "benign_false_warning_rate": sum(r[method] == positive for r in benign) / len(benign)
            if benign
            else None,
        }
    incremental = sum(
        r["jev"] == r["expected"] == "possible_contract_impact"
        and r["deterministic"] != "possible_contract_impact"
        and r["heuristic"] != "possible_contract_impact"
        for r in heldout
    )
    latencies = sorted(successful_latencies.values())
    return envelope(
        fixture_only=dataset.fixture_only,
        calls_made=0,
        successful_request_p95_ms=latencies[math.ceil(len(latencies) * 0.95) - 1]
        if latencies
        else None,
        successful_requests_with_latency=len(latencies),
        model=next(iter(models)),
        examples=len(rows),
        heldout_examples=len(heldout),
        metrics=metrics,
        incremental_discoveries=incremental,
        sample_size_target_met=len(rows) >= 200 and len(heldout) >= 120,
        promotion_approved=False,
        requires_independent_label_latency_cost_and_pilot_review=True,
        baseline_provenance="operator_supplied_predictions",
        rows=rows,
    )
