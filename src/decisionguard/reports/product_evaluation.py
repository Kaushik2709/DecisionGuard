"""Paired descriptive metrics; no causal, prevalence or release approval inference."""

import hashlib
import json
from collections import Counter
from statistics import median
from typing import Any

from decisionguard.domain.errors import require
from decisionguard.domain.product_evaluation import (
    Method,
    Observation,
    StudyObservations,
    StudyPlan,
    observation_key,
)

METHODS: tuple[Method, ...] = ("baseline", "decisionguard")
ALL_CHECKS = {"schema_validation", "codegen", "contract_tests", "integration_tests"}


def plan_digest(plan: StudyPlan) -> str:
    content = json.dumps(plan.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_study(plan: StudyPlan, data: StudyObservations) -> None:
    require(data.plan_sha256 == plan_digest(plan), "INVALID", "Study plan digest changed")
    require(
        len({observation_key(o) for o in data.observations}) == len(data.observations),
        "INVALID",
        "Duplicate case/participant/method observation",
    )
    cases = {c.id: c for c in plan.cases}
    repositories = {c.repository for c in plan.cases}
    for item in data.observations:
        require(item.case_id in cases, "INVALID", "Observation references an unplanned case")
        require(item.participant_id in plan.participants, "INVALID", "Unplanned participant")
        require(
            item.source_revision == cases[item.case_id].source_revision,
            "INVALID",
            "Paired observations must use the planned source revision",
        )
        require(
            item.observed_at >= plan.registered_at,
            "INVALID",
            "Observation predates study registration",
        )
        require(set(item.checks) <= set(plan.checks), "INVALID", "Unplanned baseline check")
    setup_keys = {(s.participant_id, s.repository, s.method) for s in data.setup}
    require(len(setup_keys) == len(data.setup), "INVALID", "Duplicate setup observation")
    for setup in data.setup:
        require(
            setup.participant_id in plan.participants and setup.repository in repositories,
            "INVALID",
            "Unplanned setup participant/repository",
        )
    require(
        len({f.participant_id for f in data.feedback}) == len(data.feedback),
        "INVALID",
        "Duplicate participant feedback",
    )
    require(
        all(f.participant_id in plan.participants for f in data.feedback),
        "INVALID",
        "Unplanned feedback participant",
    )
    require(
        plan.study_kind == "fixture" or all(f.consent_to_use for f in data.feedback),
        "INVALID",
        "Pilot feedback requires explicit consent to use the response",
    )


def fraction(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "count": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def measurement(values: list[float]) -> dict[str, Any]:
    return {"observations": len(values), "median_seconds": median(values) if values else None}


def report(plan: StudyPlan, data: StudyObservations) -> dict[str, Any]:
    validate_study(plan, data)
    lookup = {observation_key(o): o for o in data.observations}
    rows: list[dict[str, Any]] = []
    matched: dict[Method, list[tuple[str, Observation]]] = {m: [] for m in METHODS}
    deltas: dict[str, list[float]] = {
        k: []
        for k in ("detection_seconds", "elapsed_seconds", "rework_seconds", "tool_overhead_seconds")
    }
    incremental = baseline_only = 0
    for case in plan.cases:
        for participant in plan.participants:
            pair = {m: lookup.get((case.id, participant, m)) for m in METHODS}
            reasons = []
            for method, item in pair.items():
                if item is None or item.status != "completed":
                    reasons.append(f"{method}:{item.status if item else 'missing'}")
                elif any(item.checks.get(k) not in {"passed", "failed"} for k in plan.checks):
                    reasons.append(f"{method}:incomplete_baseline_checks")
            eligible = not reasons
            left, right = pair["baseline"], pair["decisionguard"]
            if eligible and left is not None and right is not None:
                matched["baseline"].append((case.expected, left))
                matched["decisionguard"].append((case.expected, right))
                for field in deltas:
                    a, b = getattr(left, field), getattr(right, field)
                    if a is not None and b is not None:
                        deltas[field].append(b - a)
                if case.expected == "harmful":
                    incremental += (
                        left.detected_before_integration is False
                        and right.detected_before_integration is True
                    )
                    baseline_only += (
                        left.detected_before_integration is True
                        and right.detected_before_integration is False
                    )
            rows.append(
                {
                    "case_id": case.id,
                    "participant_id": participant,
                    "expected": case.expected,
                    "eligible": eligible,
                    "exclusions": reasons,
                    "methods": {
                        m: item.model_dump(mode="json") if item else None
                        for m, item in pair.items()
                    },
                }
            )
    metrics: dict[str, Any] = {}
    for method in METHODS:
        runs = matched[method]
        harmful = [o for label, o in runs if label == "harmful"]
        benign = [o for label, o in runs if label == "benign"]
        known_detection = [o for o in harmful if o.detected_before_integration is not None]
        integrated = [o for o in harmful if o.integration_outcome in {"correct", "defective"}]
        known_block = [o for o in benign if o.blocked is not None]
        metrics[method] = {
            "harmful_pairs": len(harmful),
            "early_detections": fraction(
                sum(o.detected_before_integration is True for o in known_detection),
                len(known_detection),
            ),
            "unknown_detection": len(harmful) - len(known_detection),
            "escaped_defects": fraction(
                sum(o.integration_outcome == "defective" for o in integrated), len(integrated)
            ),
            "harmful_not_integrated": sum(
                o.integration_outcome == "not_integrated" for o in harmful
            ),
            "unknown_integration": sum(o.integration_outcome == "unknown" for o in harmful),
            "benign_pairs": len(benign),
            "benign_blocks": fraction(
                sum(o.blocked is True for o in known_block), len(known_block)
            ),
            "unknown_benign_block": len(benign) - len(known_block),
            "unknown_ground_truth_pairs": sum(label == "unknown" for label, _ in runs),
            "timings": {
                field: measurement(
                    [getattr(o, field) for _, o in runs if getattr(o, field) is not None]
                )
                for field in deltas
            },
            "attempt_statuses": dict(
                Counter(o.status for o in data.observations if o.method == method)
            ),
            "setup": {
                "completed": measurement(
                    [
                        s.elapsed_seconds
                        for s in data.setup
                        if s.method == method and s.status == "completed"
                    ]
                ),
                "failed": measurement(
                    [
                        s.elapsed_seconds
                        for s in data.setup
                        if s.method == method and s.status == "error"
                    ]
                ),
                "missing": len(plan.participants) * len({c.repository for c in plan.cases})
                - sum(s.method == method for s in data.setup),
            },
        }
    feedback = Counter(f.continue_using for f in data.feedback)
    return {
        "schema_version": 1,
        "study_id": plan.study_id,
        "plan_sha256": plan_digest(plan),
        "fixture_only": plan.study_kind == "fixture",
        "selection": plan.selection,
        "provenance": "operator_recorded; file hashes do not verify measurement truth or reviewer independence",
        "evidence_verification": "not_checked",
        "full_baseline_planned": set(plan.checks) == ALL_CHECKS,
        "planned_pairs": len(rows),
        "eligible_pairs": len(matched["baseline"]),
        "excluded_pairs": sum(not row["eligible"] for row in rows),
        "unique_cases": len(plan.cases),
        "repositories": len({c.repository for c in plan.cases}),
        "change_families": len({c.change_family for c in plan.cases}),
        "participants": len(plan.participants),
        "metrics": metrics,
        "incremental_early_detections": incremental,
        "baseline_only_early_detections": baseline_only,
        "paired_deltas_decisionguard_minus_baseline": {
            field: measurement(values) for field, values in deltas.items()
        },
        "feedback": {
            **{k: feedback[k] for k in ("yes", "no", "undecided", "withdrew")},
            "missing": len(plan.participants) - len(data.feedback),
            "pricing_interest": {
                k: sum(f.pricing_interest == k for f in data.feedback)
                for k in ("not_asked", "would_consider", "would_not_pay", "unknown")
            },
            "pricing_provenance": "stated interest only; no actual payments or paid demand established",
        },
        "success_criteria_for_manual_review": plan.success_criteria,
        "frequency_estimate_available": False,
        "effectiveness_claim_approved": False,
        "release_approved": False,
        "rows": rows,
    }
