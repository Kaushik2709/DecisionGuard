"""Actual schema/codegen/type/contract/HTTP checks; planted cases, never pilot evidence."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from decisionguard.application.onboarding import setup_project
from decisionguard.application.product_evaluation import evaluate_files
from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    ProposeRequest,
    ReviewRequest,
    TaskMutation,
    Value,
)
from decisionguard.domain.onboarding import ProjectSetup
from decisionguard.domain.product_evaluation import StudyPlan
from decisionguard.git.context import git
from decisionguard.reports.product_evaluation import plan_digest

SOURCE = Path(__file__).resolve().parents[2] / "examples" / "strong-baseline"
AVAILABLE = (
    shutil.which("node") is not None
    and (SOURCE / "node_modules/openapi-typescript/bin/cli.js").is_file()
    and (SOURCE / "node_modules/typescript/lib/tsc.js").is_file()
)
pytestmark = pytest.mark.skipif(
    not AVAILABLE and os.environ.get("DECISIONGUARD_REQUIRE_STRONG_BASELINE") != "1",
    reason="Optional pinned baseline Node tools are not installed; CI requires them explicitly",
)


def test_strong_baseline_paired_study_and_real_type_failure(tmp_path):
    assert AVAILABLE, "Required pinned baseline tools are missing"
    root = tmp_path / "strong baseline repository"
    shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
    git(root, "init", "-b", "main")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Baseline fixture",
    )
    command = [sys.executable, "-B", "run.py", "--tools-root", str(SOURCE)]
    setup = setup_project(
        root,
        None,
        ProjectSetup.model_validate(
            {
                "coordinator": "reviewer",
                "runner": {"argv": command, "timeout": 60, "output_limit": 64000},
                "tasks": [{"task_id": "worker", "actor": "worker", "paths": ["."]}],
            }
        ),
        apply=True,
    )
    service = Service(Path(setup["state"]))
    contract = Contract(boundary="checkout", key="amount.unit")
    major = Value(kind="money_unit", value="INR.major.decimal-string")
    proposal = service.propose(
        ProposeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key="initial",
            contract=contract,
            value=major,
            expected_version=0,
            scope=["."],
            rationale="Explicit whole-fixture unit contract",
        )
    )["proposal"]
    service.review(
        ReviewRequest(
            actor="reviewer",
            idempotency_key="accept",
            proposal_id=proposal["proposal_id"],
            accept=True,
            expected_version=0,
            rationale="Reviewed fixture",
        )
    )
    service.assume(
        AssumeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key="assume",
            contract=contract,
            expected=major,
            observed_version=1,
        )
    )
    archive = tmp_path / "study"
    archive.mkdir()

    def evidence(name, value):
        path = archive / name
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    original = (root / "client.ts").read_text(encoding="utf-8")
    clients = {"benign": original, "harmful": original.replace("amount: 499", "amount: 49900")}
    manifest = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.iterdir()
        if p.is_file() and p.name != "client.ts"
    }
    plan = {
        "schema_version": 1,
        "study_id": "strong-baseline-fixture",
        "study_kind": "fixture",
        "registered_at": datetime.now(UTC).isoformat(),
        "selection": "planted",
        "question": "Does the paired report credit a real strong baseline for the known unit mismatch?",
        "baseline_description": "JSON Schema + pinned OpenAPI codegen + strict TypeScript + adapter contract + loopback HTTP",
        "treatment_description": "Same fixed baseline under DecisionGuard source-bound runner and task gate",
        "checks": {
            "schema_validation": "jsonschema 4.26.0, schema_check.py",
            "codegen": "openapi-typescript 7.13.0 --check and TypeScript 5.9.3 --noEmit --strict",
            "contract_tests": "contract_check.py provider adapter and schema expectations",
            "integration_tests": "verify_http.py: actual Node client and Python loopback API",
        },
        "success_criteria": ["Credit baseline catches; no live-agent or adoption claims"],
        "participants": ["scripted-fixture"],
        "cases": [],
    }
    for label, client in clients.items():
        fingerprint = hashlib.sha256(
            (json.dumps(manifest, sort_keys=True) + client).encode()
        ).hexdigest()
        plan["cases"].append(
            {
                "id": label,
                "repository": "strong-baseline",
                "change_family": f"unit-{label}",
                "source_revision": fingerprint,
                "expected": label,
                "reviewed_by": ["fixture-author"],
                "label_evidence": [
                    evidence(
                        f"{label}-label.json",
                        {
                            "fixture_only": True,
                            "manifest": manifest,
                            "client": client,
                            "expected_provider_amount": 49900,
                        },
                    )
                ],
            }
        )
    plan_path = archive / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    observations = []
    try:
        for case in plan["cases"]:
            (root / "client.ts").write_text(clients[case["id"]], encoding="utf-8")
            started = time.perf_counter()
            base = subprocess.run(
                command, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60
            )
            base_seconds = time.perf_counter() - started
            baseline = json.loads(base.stdout)
            assert baseline["complete"]
            assert base.returncode == (0 if case["expected"] == "benign" else 1), (
                base.stdout + base.stderr
            )
            if case["expected"] == "harmful":
                assert baseline["checks"]["codegen"]["status"] == "passed"
                assert baseline["checks"]["integration_tests"]["status"] == "failed"
            started = time.perf_counter()
            validation = validate(
                service, TaskMutation(actor="worker", task_id="worker", idempotency_key=case["id"])
            )
            receipt = gate(service, ["worker"])
            seconds = time.perf_counter() - started
            treatment = json.loads(validation["run"]["output"])
            assert treatment["complete"] and validation["run"]["valid"]
            assert receipt["receipt"]["passed"] is (case["expected"] == "benign")
            for method, elapsed, check_results, blocked, raw in (
                ("baseline", base_seconds, baseline, not baseline["passed"], baseline),
                (
                    "decisionguard",
                    seconds,
                    treatment,
                    not receipt["receipt"]["passed"],
                    {"validation": validation, "gate": receipt},
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
                        "checks": {k: v["status"] for k, v in check_results["checks"].items()},
                        "detected_before_integration": blocked,
                        "detection_seconds": elapsed if blocked else None,
                        "blocked": blocked,
                        "elapsed_seconds": elapsed,
                        "integration_outcome": "not_integrated",
                        "evidence": [evidence(f"{case['id']}-{method}.json", raw)],
                    }
                )
        data = {
            "schema_version": 1,
            "plan_sha256": plan_digest(StudyPlan.model_validate_json(json.dumps(plan))),
            "observations": observations,
        }
        data_path = archive / "observations.json"
        data_path.write_text(json.dumps(data), encoding="utf-8")
        result = evaluate_files(plan_path, data_path)
        assert result["full_baseline_planned"] and result["eligible_pairs"] == 2
        assert result["incremental_early_detections"] == 0
        assert result["metrics"]["baseline"]["early_detections"]["rate"] == 1.0
        (archive / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        # A structurally wrong client must fail the actual compiler, not just runtime tests.
        (root / "client.ts").write_text(
            original.replace("amount: 499", 'amount: "wrong"'), encoding="utf-8"
        )
        typed = subprocess.run(
            command, cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60
        )
        output = json.loads(typed.stdout)
        assert typed.returncode == 1 and output["checks"]["codegen"]["status"] == "failed"
        assert "TS2322" in json.dumps(output["checks"]["codegen"])
        unavailable = subprocess.run(
            [*command[:-1], str(tmp_path / "absent-tools")],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert unavailable.returncode == 2
        assert json.loads(unavailable.stdout)["checks"]["codegen"]["status"] == "unsupported"
    finally:
        service.close()
