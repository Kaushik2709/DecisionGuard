"""Operator-recorded paired studies. These records never confer gate authority."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, ConfigDict, Field, model_validator

from decisionguard.domain.models import Model

Identifier = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^\S(?:.*\S)?$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Seconds = Annotated[float, Field(ge=0, le=31_536_000, allow_inf_nan=False, strict=True)]
Method = Literal["baseline", "decisionguard"]
Check = Literal["schema_validation", "codegen", "contract_tests", "integration_tests"]
CheckStatus = Literal["passed", "failed", "not_run", "unsupported", "error"]


class StudyModel(Model):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EvidenceFile(StudyModel):
    path: Annotated[str, Field(min_length=1, max_length=1000)]
    sha256: Digest


class StudyCase(StudyModel):
    id: Identifier
    repository: Identifier
    change_family: Identifier
    source_revision: Annotated[str, Field(pattern=r"^[0-9a-f]{7,64}$")]
    expected: Literal["harmful", "benign", "unknown"]
    reviewed_by: list[Identifier] = Field(min_length=1, max_length=10)
    label_evidence: list[EvidenceFile] = Field(min_length=1, max_length=10)


class StudyPlan(StudyModel):
    schema_version: Literal[1]
    study_id: Identifier
    study_kind: Literal["fixture", "pilot"]
    registered_at: AwareDatetime
    selection: Literal["planted", "consecutive", "convenience"]
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    baseline_description: Annotated[str, Field(min_length=1, max_length=4000)]
    treatment_description: Annotated[str, Field(min_length=1, max_length=4000)]
    # Each description identifies the fixed configuration, commands and tool versions.
    checks: dict[Check, Annotated[str, Field(min_length=1, max_length=2000)]] = Field(
        min_length=1, max_length=4
    )
    success_criteria: list[Annotated[str, Field(min_length=1, max_length=2000)]] = Field(
        min_length=1, max_length=20
    )
    participants: list[Identifier] = Field(min_length=1, max_length=1000)
    cases: list[StudyCase] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_plan(self) -> "StudyPlan":
        if len(set(self.participants)) != len(self.participants):
            raise ValueError("Duplicate participant")
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case")
        identities = {(c.repository, c.source_revision, c.change_family) for c in self.cases}
        if len(identities) != len(self.cases):
            raise ValueError("Reused repository/revision/change family")
        if len(self.cases) * len(self.participants) > 5000:
            raise ValueError("At most 5000 planned pairs")
        if self.study_kind == "fixture" and self.selection != "planted":
            raise ValueError("Fixtures must be labelled planted")
        return self


class Observation(StudyModel):
    case_id: Identifier
    participant_id: Identifier
    method: Method
    source_revision: Annotated[str, Field(pattern=r"^[0-9a-f]{7,64}$")]
    observed_at: AwareDatetime
    status: Literal["completed", "not_run", "unsupported", "error"]
    checks: dict[Check, CheckStatus] = Field(default_factory=dict, max_length=4)
    detected_before_integration: bool | None = None
    detection_seconds: Seconds | None = None
    blocked: bool | None = None
    integration_outcome: Literal["correct", "defective", "not_integrated", "unknown"] = "unknown"
    elapsed_seconds: Seconds | None = None
    rework_seconds: Seconds | None = None
    tool_overhead_seconds: Seconds | None = None
    evidence: list[EvidenceFile] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def coherent_observation(self) -> "Observation":
        if self.status == "completed" and not self.evidence:
            raise ValueError("Completed observations require evidence")
        if self.detected_before_integration is True and self.detection_seconds is None:
            raise ValueError("A detection requires elapsed time from change availability")
        if self.detected_before_integration is not True and self.detection_seconds is not None:
            raise ValueError("Detection time requires a detection")
        if (
            self.detection_seconds is not None
            and self.elapsed_seconds is not None
            and self.detection_seconds > self.elapsed_seconds
        ):
            raise ValueError("Detection cannot follow the end of the observation")
        if self.status != "completed" and (
            self.detected_before_integration is not None
            or self.blocked is not None
            or self.integration_outcome != "unknown"
        ):
            raise ValueError("Unfinished runs cannot assert outcomes")
        return self


class SetupObservation(StudyModel):
    participant_id: Identifier
    repository: Identifier
    method: Method
    status: Literal["completed", "error"]
    elapsed_seconds: Seconds
    evidence: list[EvidenceFile] = Field(min_length=1, max_length=10)


class Feedback(StudyModel):
    participant_id: Identifier
    continue_using: Literal["yes", "no", "undecided", "withdrew"]
    consent_to_use: bool = False
    pricing_interest: Literal["not_asked", "would_consider", "would_not_pay", "unknown"] = (
        "not_asked"
    )
    monthly_budget_minor: int | None = Field(default=None, ge=0, le=1_000_000_000)
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None = None
    evidence: list[EvidenceFile] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def coherent_pricing(self) -> "Feedback":
        if (self.monthly_budget_minor is None) != (self.currency is None):
            raise ValueError("Budget and currency must be supplied together")
        if self.monthly_budget_minor is not None and self.pricing_interest != "would_consider":
            raise ValueError("A stated budget requires explicit pricing interest")
        return self


class StudyObservations(StudyModel):
    schema_version: Literal[1]
    plan_sha256: Digest
    observations: list[Observation] = Field(default_factory=list, max_length=10000)
    setup: list[SetupObservation] = Field(default_factory=list, max_length=10000)
    feedback: list[Feedback] = Field(default_factory=list, max_length=1000)


def observation_key(item: Observation) -> tuple[str, str, Method]:
    return item.case_id, item.participant_id, item.method
