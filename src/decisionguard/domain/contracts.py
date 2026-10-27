from typing import Literal

from pydantic import Field

from decisionguard.domain.models import Contract, Model, Mutation, Name, Value


class UnitBinding(Model):
    pointer: str = Field(min_length=1, max_length=1000)
    contract: Contract
    value: Value


class OperationBinding(Model):
    method: Literal["get", "post", "put", "patch", "delete", "head", "options", "trace"]
    path: str = Field(min_length=1, max_length=1000)
    direction: Literal["request", "response", "security"]
    status: str = Field(default="200", min_length=3, max_length=7)
    contract: Contract
    scope: list[str] = Field(min_length=1, max_length=100)
    producers: list[Name] = Field(default_factory=list, max_length=100)
    consumers: list[Name] = Field(default_factory=list, max_length=100)
    units: list[UnitBinding] = Field(default_factory=list, max_length=100)


class ContractScan(Model):
    task_id: Name
    spec: str = Field(min_length=1, max_length=1000)
    bindings: list[OperationBinding] = Field(min_length=1, max_length=100)


class ContractPublish(Mutation):
    scan: ContractScan
    preview_digest: str = Field(min_length=64, max_length=64)
    expected_versions: dict[str, int]
    rationale: str = Field(min_length=1, max_length=8000)
