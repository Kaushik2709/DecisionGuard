"""Explicit local setup intent. Accepted contracts and assumptions are never inferred."""

from pydantic import Field, model_validator

from decisionguard.domain.models import Contract, Model, Name, RunnerConfig


class SetupTask(Model):
    task_id: Name
    actor: Name
    worktree: str = "."
    paths: list[str] = Field(min_length=1, max_length=100)
    contracts: list[Contract] = Field(default_factory=list, max_length=100)
    integration: bool = False


class ProjectSetup(Model):
    coordinator: Name
    runner: RunnerConfig
    tasks: list[SetupTask] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_tasks(self) -> "ProjectSetup":
        if len({t.task_id for t in self.tasks}) != len(self.tasks):
            raise ValueError("Duplicate task ID")
        if any(t.integration for t in self.tasks) and not any(
            not t.integration for t in self.tasks
        ):
            raise ValueError("Include an implementation task alongside integration")
        return self
