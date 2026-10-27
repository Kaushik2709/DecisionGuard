"""Synthetic observations test arithmetic and rejection, never product effectiveness."""

import hashlib
import json

import pytest
from pydantic import ValidationError

from decisionguard.application.product_evaluation import evaluate_files, inspect_plan
from decisionguard.domain.errors import GuardError
from decisionguard.domain.product_evaluation import StudyObservations, StudyPlan
from decisionguard.reports.product_evaluation import plan_digest, report


def study(tmp_path, labels=("harmful", "harmful", "benign", "unknown")):
    log = tmp_path / "fixture.log"
    log.write_bytes(b"Synthetic observations for arithmetic tests, not a pilot.\n")
    evidence = {"path": log.name, "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
    plan = {
        "schema_version": 1,
        "study_id": "arithmetic-fixture",
        "study_kind": "fixture",
        "registered_at": "2026-10-20T00:00:00Z",
        "selection": "planted",
        "question": "Test paired descriptive arithmetic",
        "baseline_description": "Synthetic test inputs",
        "treatment_description": "Synthetic test inputs plus gate observations",
        "checks": {
            k: "Synthetic test configuration"
            for k in ("schema_validation", "codegen", "contract_tests", "integration_tests")
        },
        "success_criteria": ["No effectiveness claims from synthetic observations"],
        "participants": ["fixture-operator"],
        "cases": [
            {
                "id": str(i),
                "repository": "fixture-repo",
                "change_family": f"family-{i}",
                "source_revision": "a" * 40,
                "expected": label,
                "reviewed_by": ["fixture-author"],
                "label_evidence": [evidence],
            }
            for i, label in enumerate(labels)
        ],
    }
    observations = []
    for case in plan["cases"]:
        for method in ("baseline", "decisionguard"):
            detected = case["expected"] == "harmful" and (
                method == "decisionguard" or case["id"] == "1"
            )
            observations.append(
                {
                    "case_id": case["id"],
                    "participant_id": "fixture-operator",
                    "method": method,
                    "source_revision": "a" * 40,
                    "observed_at": "2026-10-20T01:00:00Z",
                    "status": "completed",
                    "checks": {k: "passed" for k in plan["checks"]},
                    "detected_before_integration": detected,
                    "detection_seconds": (10.0 if method == "baseline" else 2.0)
                    if detected
                    else None,
                    "blocked": method == "decisionguard",
                    "integration_outcome": "defective"
                    if case["id"] == "0" and method == "baseline"
                    else "correct",
                    "elapsed_seconds": 20.0 if method == "baseline" else 25.0,
                    "rework_seconds": 12.0 if method == "baseline" else 4.0,
                    "tool_overhead_seconds": 0.0 if method == "baseline" else 3.0,
                    "evidence": [evidence],
                }
            )
    model = StudyPlan.model_validate_json(json.dumps(plan))
    data = {
        "schema_version": 1,
        "plan_sha256": plan_digest(model),
        "observations": observations,
        "setup": [],
        "feedback": [],
    }
    return plan, data


def calculate(plan, data):
    return report(
        StudyPlan.model_validate_json(json.dumps(plan)),
        StudyObservations.model_validate_json(json.dumps(data)),
    )


def write_study(tmp_path, plan, data):
    plan_path, data_path = tmp_path / "plan.json", tmp_path / "observations.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    data_path.write_text(json.dumps(data), encoding="utf-8")
    return plan_path, data_path


def test_paired_metrics_credit_baseline_and_expose_costs(tmp_path):
    plan, data = study(tmp_path)
    result = calculate(plan, data)
    assert result["eligible_pairs"] == 4
    assert result["incremental_early_detections"] == 1
    assert result["metrics"]["baseline"]["early_detections"]["rate"] == 0.5
    assert result["metrics"]["baseline"]["escaped_defects"]["rate"] == 0.5
    assert result["metrics"]["decisionguard"]["benign_blocks"]["rate"] == 1.0
    deltas = result["paired_deltas_decisionguard_minus_baseline"]
    assert deltas["detection_seconds"] == {"observations": 1, "median_seconds": -8.0}
    assert deltas["rework_seconds"]["median_seconds"] == -8.0
    assert deltas["elapsed_seconds"]["median_seconds"] == 5.0
    assert result["metrics"]["baseline"]["unknown_ground_truth_pairs"] == 1
    assert not result["effectiveness_claim_approved"] and not result["release_approved"]
    assert not result["frequency_estimate_available"]


def test_baseline_only_detection_is_retained(tmp_path):
    plan, data = study(tmp_path, ("harmful",))
    data["observations"][0].update(detected_before_integration=True, detection_seconds=1.0)
    data["observations"][1].update(detected_before_integration=False, detection_seconds=None)
    result = calculate(plan, data)
    assert result["baseline_only_early_detections"] == 1
    assert result["incremental_early_detections"] == 0


def test_duplicate_planned_case_cannot_inflate_independent_changes(tmp_path):
    plan, _ = study(tmp_path)
    plan["cases"][1]["change_family"] = plan["cases"][0]["change_family"]
    with pytest.raises(ValidationError, match="Reused"):
        StudyPlan.model_validate_json(json.dumps(plan))


def test_missing_error_and_unsupported_are_excluded_not_success(tmp_path):
    plan, data = study(tmp_path)
    data["observations"] = data["observations"][:6]
    for index, status in ((1, "error"), (3, "unsupported")):
        item = data["observations"][index]
        item.update(
            status=status,
            detected_before_integration=None,
            detection_seconds=None,
            blocked=None,
            integration_outcome="unknown",
        )
    data["observations"][5]["checks"]["codegen"] = "not_run"
    result = calculate(plan, data)
    assert result["planned_pairs"] == result["excluded_pairs"] == 4
    assert result["eligible_pairs"] == result["incremental_early_detections"] == 0
    assert result["metrics"]["baseline"]["early_detections"]["rate"] is None
    assert result["rows"][3]["exclusions"] == ["baseline:missing", "decisionguard:missing"]


def test_unknown_measurements_and_unintegrated_are_not_escaped_or_safe(tmp_path):
    plan, data = study(tmp_path, ("harmful",))
    for item in data["observations"]:
        item.update(
            detected_before_integration=None,
            detection_seconds=None,
            blocked=None,
            integration_outcome="not_integrated",
            rework_seconds=None,
        )
    result = calculate(plan, data)
    assert result["metrics"]["baseline"]["escaped_defects"]["rate"] is None
    assert result["metrics"]["baseline"]["unknown_detection"] == 1
    assert result["metrics"]["baseline"]["harmful_not_integrated"] == 1
    assert (
        result["paired_deltas_decisionguard_minus_baseline"]["rework_seconds"]["observations"] == 0
    )


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("duplicate", "Duplicate"),
        ("revision", "revision"),
        ("digest", "digest"),
        ("participant", "participant"),
        ("case", "case"),
        ("timestamp", "predates"),
    ],
)
def test_invalid_pairing_is_rejected(tmp_path, mutation, match):
    plan, data = study(tmp_path)
    if mutation == "duplicate":
        data["observations"].append(data["observations"][0])
    elif mutation == "digest":
        plan["question"] = "Changed plan after observations"
    else:
        field, value = {
            "revision": ("source_revision", "b" * 40),
            "participant": ("participant_id", "unplanned"),
            "case": ("case_id", "unplanned"),
            "timestamp": ("observed_at", "2026-10-19T00:00:00Z"),
        }[mutation]
        data["observations"][0][field] = value
    with pytest.raises(GuardError, match=match):
        calculate(plan, data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("elapsed_seconds", -1.0),
        ("rework_seconds", float("nan")),
        ("tool_overhead_seconds", float("inf")),
        ("blocked", "false"),
        ("status", "success"),
        ("detection_seconds", 1000.0),
    ],
)
def test_malformed_or_incoherent_observations_rejected(tmp_path, field, value):
    plan, data = study(tmp_path)
    data["observations"][1][field] = value
    with pytest.raises(ValidationError):
        calculate(plan, data)


def test_file_integrity_and_stable_plan_digest(tmp_path):
    plan, data = study(tmp_path)
    plan_path, data_path = write_study(tmp_path, plan, data)
    assert inspect_plan(plan_path)["plan_sha256"] == data["plan_sha256"]
    result = evaluate_files(plan_path, data_path)
    assert result["evidence_files_verified"] == 1
    assert result["evidence_verification"] == "sha256_matched_local_files"
    (tmp_path / "fixture.log").write_text("Edited log")
    with pytest.raises(GuardError, match="digest mismatch"):
        evaluate_files(plan_path, data_path)


@pytest.mark.parametrize(
    "path", ["../elsewhere.log", "C:/private.log", "C:private.log", "\\\\host\\share\\log"]
)
def test_evidence_paths_cannot_escape_document_directory(tmp_path, path):
    plan, data = study(tmp_path)
    data["observations"][0]["evidence"][0]["path"] = path
    # The helper deliberately shares this evidence record with label evidence.
    plan_path, data_path = write_study(tmp_path, plan, data)
    with pytest.raises(GuardError, match="relative"):
        inspect_plan(plan_path)


def test_evidence_limits_and_missing_files(tmp_path, monkeypatch):
    from decisionguard.application import product_evaluation as module

    plan, data = study(tmp_path)
    paths = write_study(tmp_path, plan, data)
    monkeypatch.setattr(module, "EVIDENCE_FILE_LIMIT", 1)
    with pytest.raises(GuardError, match="byte limit"):
        evaluate_files(*paths)
    (tmp_path / "fixture.log").unlink()
    with pytest.raises(GuardError, match="missing"):
        evaluate_files(*paths)


def test_symlinked_evidence_outside_archive_is_rejected(tmp_path):
    from decisionguard.application.product_evaluation import EvidenceVerifier
    from decisionguard.domain.product_evaluation import EvidenceFile

    archive = tmp_path / "archive"
    archive.mkdir()
    target = tmp_path / "outside.log"
    target.write_bytes(b"outside")
    try:
        (archive / "link.log").symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks requires Windows developer mode or privileges")
    with pytest.raises(GuardError, match="outside"):
        EvidenceVerifier().check(
            archive,
            EvidenceFile(path="link.log", sha256=hashlib.sha256(target.read_bytes()).hexdigest()),
        )


def test_setup_failures_and_feedback_include_missing_participants(tmp_path):
    plan, data = study(tmp_path)
    evidence = data["observations"][0]["evidence"]
    data["setup"] = [
        {
            "participant_id": "fixture-operator",
            "repository": "fixture-repo",
            "method": "decisionguard",
            "status": "error",
            "elapsed_seconds": 120.0,
            "evidence": evidence,
        }
    ]
    data["feedback"] = [
        {"participant_id": "fixture-operator", "continue_using": "withdrew", "evidence": evidence}
    ]
    result = calculate(plan, data)
    assert result["metrics"]["decisionguard"]["setup"]["failed"]["median_seconds"] == 120.0
    assert result["metrics"]["baseline"]["setup"]["missing"] == 1
    assert result["feedback"]["withdrew"] == 1 and result["feedback"]["missing"] == 0
    data["feedback"].append(data["feedback"][0])
    with pytest.raises(GuardError, match="Duplicate participant feedback"):
        calculate(plan, data)


def test_pilot_feedback_requires_consent_and_pricing_is_only_stated_interest(tmp_path):
    plan, data = study(tmp_path)
    plan["study_kind"] = "pilot"
    data["plan_sha256"] = plan_digest(StudyPlan.model_validate_json(json.dumps(plan)))
    data["feedback"] = [
        {
            "participant_id": "fixture-operator",
            "continue_using": "yes",
            "pricing_interest": "would_consider",
            "monthly_budget_minor": 50000,
            "currency": "INR",
            "evidence": data["observations"][0]["evidence"],
        }
    ]
    with pytest.raises(GuardError, match="consent"):
        calculate(plan, data)
    data["feedback"][0]["consent_to_use"] = True
    result = calculate(plan, data)
    assert result["feedback"]["pricing_interest"]["would_consider"] == 1
    assert "no actual payments" in result["feedback"]["pricing_provenance"]
    data["feedback"][0]["currency"] = None
    with pytest.raises(ValidationError, match="together"):
        calculate(plan, data)


def test_pilot_kit_is_portable_empty_and_preserves_label_integrity(tmp_path):
    from decisionguard.application.product_evaluation import create_pilot_kit

    plan, data = study(tmp_path)
    paths = write_study(tmp_path, plan, data)
    destination = tmp_path / "kit"
    result = create_pilot_kit(paths[0], destination)
    assert result["observations_collected"] == result["feedback_collected"] == 0
    report = evaluate_files(destination / "plan.json", destination / "observations.json")
    assert report["eligible_pairs"] == 0 and report["feedback"]["missing"] == 1
    assert (destination / "PARTICIPANT_GUIDE.md").is_file()
    with pytest.raises(GuardError, match="new pilot"):
        create_pilot_kit(paths[0], destination)
