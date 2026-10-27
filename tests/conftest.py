import sys
import uuid

import pytest

from decisionguard.application.config import initialize
from decisionguard.application.services import Service
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    ProposeRequest,
    ReviewRequest,
    RunnerConfig,
    TaskRequest,
    Value,
)
from decisionguard.git.context import git

CONTRACT = Contract(boundary="api.request", key="amount.unit")
MAJOR = Value(kind="money_unit", value="INR.major.decimal-string")
MINOR = Value(kind="money_unit", value="INR.minor.integer")


def key():
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def isolated_git_discovery(tmp_path, monkeypatch):
    # Fixtures under artifacts must not accidentally discover the real parent repository.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


def accept(service, proposal, accept=True):
    return service.review(
        ReviewRequest(
            actor="coordinator",
            idempotency_key=key(),
            proposal_id=proposal["proposal"]["proposal_id"],
            accept=accept,
            expected_version=proposal["proposal"]["expected_version"],
            rationale="Reviewed fixture",
        )
    )


def proposal(service, value=MINOR, expected_version=1):
    return service.propose(
        ProposeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=CONTRACT,
            value=value,
            expected_version=expected_version,
            scope=["code.py", "check.py"],
            rationale="Fixture contract change",
        )
    )


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "repository with spaces"
    root.mkdir()
    git(root, "init", "-b", "main")
    (root / "code.py").write_text("amount = '499.00'\n")
    (root / "check.py").write_text("from code import amount\nassert amount\n")
    (root / ".gitignore").write_text("__pycache__/\n")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        "Initial",
    )
    state = initialize(root, None, "coordinator", RunnerConfig(argv=[sys.executable, "check.py"]))
    service = Service(state)
    service.register(
        TaskRequest(
            actor="worker",
            task_id="worker",
            worktree=str(root),
            paths=["code.py", "check.py"],
            idempotency_key=key(),
            completed=True,
        )
    )
    accept(service, proposal(service, MAJOR, 0))
    service.assume(
        AssumeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=CONTRACT,
            expected=MAJOR,
            observed_version=1,
            evidence=["code.py"],
        )
    )
    return service, root
