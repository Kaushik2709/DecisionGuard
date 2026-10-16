from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Name = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[\w.:@/ -]+$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Contract(Model):
    boundary: Name
    key: Name

    @field_validator("boundary", "key")
    @classmethod
    def unambiguous_identity(cls, value: str) -> str:
        if "::" in value:
            raise ValueError("Contract identity components cannot contain ::")
        return value

    @property
    def identity(self) -> str:
        return f"{self.boundary}::{self.key}"


class Value(Model):
    kind: Literal[
        "money_unit",
        "time_unit",
        "schema",
        "auth",
        "error_format",
        "retry_policy",
        "idempotency",
        "text",
    ]
    value: Annotated[str, Field(min_length=1, max_length=4000)]
    deleted: bool = False


class Mutation(Model):
    actor: Name
    idempotency_key: Annotated[str, Field(min_length=1, max_length=200)]


class TaskRequest(Mutation):
    task_id: Name
    worktree: str
    paths: list[str] = Field(min_length=1, max_length=100)
    contracts: list[Contract] = Field(default_factory=list, max_length=100)
    integration: bool = False
    completed: bool = False


class AssumeRequest(Mutation):
    task_id: Name
    contract: Contract
    expected: Value
    observed_version: int = Field(ge=1)
    evidence: list[str] = Field(default_factory=list, max_length=100)


class ProposeRequest(Mutation):
    task_id: Name
    contract: Contract
    value: Value
    expected_version: int = Field(ge=0)
    scope: list[str] = Field(min_length=1, max_length=100)
    rationale: str = Field(min_length=1, max_length=8000)
    evidence: list[str] = Field(default_factory=list, max_length=100)


class ReviewRequest(Mutation):
    proposal_id: Name
    accept: bool
    expected_version: int = Field(ge=0)
    rationale: str = Field(min_length=1, max_length=8000)


class TaskMutation(Mutation):
    task_id: Name


class AckRequest(TaskMutation):
    event_id: int = Field(ge=1)


class ScopeApproval(TaskMutation):
    paths: list[str] = Field(min_length=1, max_length=100)
    expected_scope_revision: int = Field(ge=0)


class ResourceLimits(Model):
    pending_per_actor: int = Field(default=20, ge=1)
    pending_per_project: int = Field(default=100, ge=1)
    tasks_per_actor: int = Field(default=100, ge=1)
    tasks_per_project: int = Field(default=1000, ge=1)
    snapshot_files: int = Field(default=100000, ge=1)
    snapshot_name_bytes: int = Field(default=16777216, ge=1)
    snapshot_file_bytes: int = Field(default=104857600, ge=1)
    snapshot_total_bytes: int = Field(default=1073741824, ge=1)
    snapshot_seconds: float = Field(default=60, gt=0)


class MappingRequest(Mutation):
    source: Contract
    target: Contract
    source_value: Value
    target_value: Value
    rationale: str = Field(min_length=1, max_length=8000)
    evidence: list[str] = Field(min_length=1, max_length=100)


class RunnerConfig(Model):
    argv: list[str] = Field(min_length=1, max_length=100)
    cwd: str = "."
    timeout: int = Field(default=60, ge=1, le=3600)
    output_limit: int = Field(default=16000, ge=100, le=1000000)


class Config(Model):
    schema_version: Literal[1] = 1
    project: str
    root: str
    common_dir: str | None
    coordinators: list[Name] = Field(min_length=1)
    runner: RunnerConfig
    task_runners: dict[str, RunnerConfig] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    limits: ResourceLimits = Field(default_factory=ResourceLimits)


class DecisionVersion(Model):
    contract: Contract
    version: int = Field(ge=1)
    value: Value
    scope: list[str] = Field(min_length=1, max_length=100)
    owner: Name
    rationale: str = Field(min_length=1, max_length=8000)
    predecessor: int | None = Field(default=None, ge=1)
    evidence: list[str] = Field(default_factory=list, max_length=100)
    timestamp: str = Field(min_length=1, max_length=100)


class ReviewedMapping(Model):
    mapping_id: Name
    actor: Name
    source: Contract
    target: Contract
    source_value: Value
    target_value: Value
    rationale: str = Field(min_length=1, max_length=8000)
    evidence: list[str] = Field(min_length=1, max_length=100)


class PortableMetadata(Model):
    schema_version: Literal[1]
    origin_project: str = Field(min_length=1, max_length=200)
    origin_revision: int = Field(ge=0)
    versions: list[DecisionVersion] = Field(max_length=10000)
    heads: dict[str, Annotated[int, Field(ge=1)]]
    mappings: list[ReviewedMapping] = Field(max_length=10000)
