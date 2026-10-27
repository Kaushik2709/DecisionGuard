from pydantic import Field

from decisionguard.domain.models import Contract, Model, Name


class AdviceCandidate(Model):
    contract: Contract
    paths: list[str] = Field(min_length=1, max_length=10)


class AdviceRequest(Model):
    task_id: Name
    model: str = Field(pattern=r"^jev-\d+\.\d+\.\d+$", max_length=100)
    candidates: list[AdviceCandidate] = Field(min_length=1, max_length=5)
    attempt: int = Field(default=0, ge=0, le=1000000)
