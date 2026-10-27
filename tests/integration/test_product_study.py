"""Exercise actual baseline checks, source-bound runner/gates, and the reporting CLI."""

import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime

from decisionguard.application.validation import gate, validate
from decisionguard.domain.models import TaskMutation


def test_actual_baseline_detection_is_not_credited_as_incremental(project, tmp_path):
    service, root = project
    evidence_root = tmp_path / "study"
    evidence_root.mkdir()

    def evidence(name, content):
        path = evidence_root / name
        path.write_text(json.dumps(content, sort_keys=True), encoding="utf-8")
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def cli(*args):
        result = subprocess.run(
            [sys.executable, "-m", "decisionguard.adapters.cli", *map(str, args)],
            cwd=evidence_root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    check = "from code import amount\nassert int(float(amount) * 100) == 49900\n"
    sources = {"benign": "amount = '499.00'\n", "harmful": "amount = '49900'\n"}
    plan = {
        "schema_version": 1,
        "study_id": "actual-local-check-fixture",
        "study_kind": "fixture",
        "registered_at": datetime.now(UTC).isoformat(),
        "selection": "planted",
        "question": "Does the report credit the baseline for catching the same unit mismatch?",
        "baseline_description": "Python combined amount/conversion assertion; no schema/codegen baseline",
        "treatment_description": "Identical check plus actual DecisionGuard validation and task gate",
        "checks": {"integration_tests": "Python check.py: assert converted checkout equals 49900"},
        "success_criteria": ["Credit baseline detection; do not infer effectiveness from fixtures"],
        "participants": ["scripted-fixture"],
        "cases": [
            {
                "id": label,
                "repository": "disposable-checkout",
                "change_family": f"unit-{label}",
                "source_revision": hashlib.sha256((source + check).encode()).hexdigest(),
                "expected": label,
                "reviewed_by": ["fixture-author"],
                "label_evidence": [
                    evidence(
                        f"{label}-label.json",
                        {
                            "fixture_only": True,
                            "source": source,
                            "check": check,
                            "rationale": "499 major units maps to 49900 paise; 49900 major units does not",
                        },
                    )
                ],
            }
            for label, source in sources.items()
        ],
    }
    plan_path = evidence_root / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    digest = cli("evaluation", "plan", plan_path)["plan_sha256"]
    observations = []
    for case in plan["cases"]:
        (root / "code.py").write_text(sources[case["id"]], encoding="utf-8")
        (root / "check.py").write_text(check, encoding="utf-8")
        started = time.perf_counter()
        baseline = subprocess.run(
            [sys.executable, "-B", "check.py"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        baseline_seconds = time.perf_counter() - started
        assert baseline.returncode == (0 if case["expected"] == "benign" else 1)
        if baseline.returncode:
            assert "AssertionError" in baseline.stderr
        started = time.perf_counter()
        result = validate(
            service,
            TaskMutation(actor="worker", task_id="worker", idempotency_key=f"study-{case['id']}"),
        )
        receipt = gate(service, ["worker"])
        treatment_seconds = time.perf_counter() - started
        assert receipt["receipt"]["passed"] is (case["expected"] == "benign")
        for method, seconds, blocked, check_passed, artifact in (
            (
                "baseline",
                baseline_seconds,
                baseline.returncode != 0,
                baseline.returncode == 0,
                {
                    "returncode": baseline.returncode,
                    "stdout": baseline.stdout,
                    "stderr": baseline.stderr,
                },
            ),
            (
                "decisionguard",
                treatment_seconds,
                not receipt["receipt"]["passed"],
                result["run"]["passed"],
                {"validation": result, "gate": receipt},
            ),
        ):
            observations.append(
                {
                    "case_id": case["id"],
                    "participant_id": "scripted-fixture",
                    "method": method,
                    "source_revision": case["source_revision"],
                    "observed_at": datetime.now(UTC).isoformat(),
                    "status": "completed",
                    "checks": {"integration_tests": "passed" if check_passed else "failed"},
                    "detected_before_integration": blocked,
                    "detection_seconds": seconds if blocked else None,
                    "blocked": blocked,
                    "integration_outcome": "not_integrated",
                    "elapsed_seconds": seconds,
                    "evidence": [evidence(f"{case['id']}-{method}.json", artifact)],
                }
            )
    data_path = evidence_root / "observations.json"
    data_path.write_text(
        json.dumps({"schema_version": 1, "plan_sha256": digest, "observations": observations}),
        encoding="utf-8",
    )
    result = cli("evaluation", "report", plan_path, data_path)
    assert result["fixture_only"] and not result["full_baseline_planned"]
    assert result["eligible_pairs"] == 2 and result["evidence_files_verified"] == 6
    assert result["incremental_early_detections"] == 0
    assert result["metrics"]["baseline"]["early_detections"]["rate"] == 1.0
    assert result["metrics"]["decisionguard"]["early_detections"]["rate"] == 1.0
    assert result["metrics"]["decisionguard"]["benign_blocks"]["rate"] == 0.0
    assert result["metrics"]["baseline"]["escaped_defects"]["rate"] is None
    (evidence_root / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
