"""Read bounded local study files and verify evidence without running any commands."""

import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any

from decisionguard.domain.errors import require
from decisionguard.domain.product_evaluation import EvidenceFile, StudyObservations, StudyPlan
from decisionguard.reports.product_evaluation import plan_digest, report, validate_study

JSON_LIMIT = 16 * 1024 * 1024
EVIDENCE_FILE_LIMIT = 4 * 1024 * 1024
EVIDENCE_TOTAL_LIMIT = 64 * 1024 * 1024
EVIDENCE_COUNT_LIMIT = 2048


def read_json(path: Path) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(JSON_LIMIT + 1)
    require(len(content) <= JSON_LIMIT, "RESOURCE_LIMIT", "Study JSON exceeds 16 MiB")
    return content


class EvidenceVerifier:
    def __init__(self) -> None:
        self.hashes: dict[Path, str] = {}
        self.total_bytes = 0

    def check(self, root: Path, evidence: EvidenceFile) -> None:
        portable = PureWindowsPath(evidence.path)
        require(
            not portable.drive
            and not portable.root
            and not Path(evidence.path).is_absolute()
            and ".." not in evidence.path.replace("\\", "/").split("/"),
            "INVALID",
            "Evidence must be relative without traversal",
        )
        base = root.resolve()
        path = (base / evidence.path).resolve()
        require(
            path.is_relative_to(base), "INVALID", "Evidence resolves outside its document directory"
        )
        if path not in self.hashes:
            require(
                len(self.hashes) < EVIDENCE_COUNT_LIMIT,
                "RESOURCE_LIMIT",
                "Too many evidence files",
            )
            require(path.is_file(), "NOT_FOUND", "Study evidence file is missing")
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                while chunk := stream.read(65536):
                    size += len(chunk)
                    self.total_bytes += len(chunk)
                    require(
                        size <= EVIDENCE_FILE_LIMIT and self.total_bytes <= EVIDENCE_TOTAL_LIMIT,
                        "RESOURCE_LIMIT",
                        "Study evidence exceeds per-file or total byte limit",
                    )
                    digest.update(chunk)
            self.hashes[path] = digest.hexdigest()
        require(self.hashes[path] == evidence.sha256, "INVALID", "Study evidence digest mismatch")


def load_plan(path: Path) -> StudyPlan:
    return StudyPlan.model_validate_json(read_json(path))


def inspect_plan(path: Path) -> dict[str, Any]:
    plan = load_plan(path)
    verifier = EvidenceVerifier()
    for case in plan.cases:
        for evidence in case.label_evidence:
            verifier.check(path.parent, evidence)
    return {
        "schema_version": 1,
        "plan_sha256": plan_digest(plan),
        "plan": plan.model_dump(mode="json"),
        "evidence_files_verified": len(verifier.hashes),
        "registration_attested": False,
    }


def evaluate_files(plan_path: Path, observations_path: Path) -> dict[str, Any]:
    plan = load_plan(plan_path)
    data = StudyObservations.model_validate_json(read_json(observations_path))
    validate_study(plan, data)
    verifier = EvidenceVerifier()
    for case in plan.cases:
        for evidence in case.label_evidence:
            verifier.check(plan_path.parent, evidence)
    groups = (
        [o.evidence for o in data.observations]
        + [s.evidence for s in data.setup]
        + [f.evidence for f in data.feedback]
    )
    for group in groups:
        for evidence in group:
            verifier.check(observations_path.parent, evidence)
    result = report(plan, data)
    result.update(
        evidence_verification="sha256_matched_local_files",
        evidence_files_verified=len(verifier.hashes),
        evidence_bytes_verified=verifier.total_bytes,
    )
    return result


def create_pilot_kit(plan_path: Path, destination: Path) -> dict[str, Any]:
    """Copy reviewed labels into a new portable archive with zero fabricated observations."""
    plan = load_plan(plan_path)
    require(not destination.exists(), "INVALID", "Choose a new pilot archive directory")
    verifier = EvidenceVerifier()
    contents: dict[str, bytes] = {}
    cases = []
    for case in plan.cases:
        labels = []
        for evidence in case.label_evidence:
            verifier.check(plan_path.parent, evidence)
            with (plan_path.parent / evidence.path).open("rb") as stream:
                content = stream.read(EVIDENCE_FILE_LIMIT + 1)
            require(
                len(content) <= EVIDENCE_FILE_LIMIT
                and hashlib.sha256(content).hexdigest() == evidence.sha256,
                "INVALID",
                "Label changed while preparing the pilot archive",
            )
            name = f"labels/{evidence.sha256}.bin"
            contents[name] = content
            labels.append(EvidenceFile(path=name, sha256=evidence.sha256))
        cases.append(case.model_copy(update={"label_evidence": labels}))
    copied = plan.model_copy(update={"cases": cases})
    destination.mkdir(parents=True)
    (destination / "labels").mkdir()
    for name, content in contents.items():
        (destination / name).write_bytes(content)
    (destination / "plan.json").write_text(copied.model_dump_json(indent=2), encoding="utf-8")
    data = StudyObservations(schema_version=1, plan_sha256=plan_digest(copied))
    (destination / "observations.json").write_text(data.model_dump_json(indent=2), encoding="utf-8")
    (destination / "observations.schema.json").write_text(
        json.dumps(StudyObservations.model_json_schema(), indent=2), encoding="utf-8"
    )
    (destination / "PARTICIPANT_GUIDE.md").write_text(
        "# Pilot archive - no results collected\n\n"
        "Review plan.json and retain its digest before running the matched tasks.\n"
        "Participation is optional. Use aliases and retain consent before using feedback.\n"
        "Do not include secrets, raw private source or identifying contact details.\n\n"
        "For each arm, record actual commands, starting/final source, failures, elapsed/rework/"
        "tool time and downstream outcomes. Leave missing measurements unknown.\n\n"
        "Ask after both arms: Would you continue using DecisionGuard (yes/no/undecided/withdrew)?\n"
        "What blocked or helped you? Would you consider paying, decline, or need more information?\n"
        "If volunteered, record monthly budget in minor units with a three-letter currency.\n"
        "Set consent_to_use=true only after consent. Pricing interest is not payment evidence.\n\n"
        "Keep exact response artifacts and SHA-256 references. Submit no feedback record until\n"
        "a real response and evidence exist. See observations.schema.json for the exact format.\n",
        encoding="utf-8",
    )
    return {
        "schema_version": 1,
        "destination": str(destination.resolve()),
        "plan_sha256": plan_digest(copied),
        "fixture_only": copied.study_kind == "fixture",
        "observations_collected": 0,
        "feedback_collected": 0,
        "publication_performed": False,
    }
