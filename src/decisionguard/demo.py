import sys
import uuid
from pathlib import Path
from typing import Any

from decisionguard.application.config import initialize
from decisionguard.application.services import Service, envelope
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import require
from decisionguard.domain.models import (
    AckRequest,
    AssumeRequest,
    Contract,
    MappingRequest,
    ProposeRequest,
    ReviewRequest,
    RunnerConfig,
    TaskMutation,
    TaskRequest,
    Value,
)
from decisionguard.git.context import git

PUBLIC = Contract(boundary="checkout.public.request", key="amount.unit")
PROVIDER = Contract(boundary="checkout.provider.request", key="amount.unit")
MAJOR = Value(kind="money_unit", value="INR.major.decimal-string")
MINOR = Value(kind="money_unit", value="INR.minor.integer")
SCOPES = ["frontend.py", "backend.py", "test_frontend.py", "test_backend.py", "test_combined.py"]


def key() -> str:
    return str(uuid.uuid4())


def review(service: Service, proposal: dict[str, Any], accept: bool = True) -> dict[str, Any]:
    item = proposal["proposal"]
    return service.review(
        ReviewRequest(
            actor="coordinator",
            idempotency_key=key(),
            proposal_id=item["proposal_id"],
            accept=accept,
            expected_version=item["expected_version"],
            rationale="Explicit local demo review",
        )
    )


def establish(service: Service, contract: Contract, value: Value) -> None:
    review(
        service,
        service.propose(
            ProposeRequest(
                actor="author",
                task_id="bootstrap",
                idempotency_key=key(),
                contract=contract,
                value=value,
                expected_version=0,
                scope=SCOPES,
                rationale="Initial reviewed contract",
            )
        ),
    )


def declare(service: Service, task_id: str, contract: Contract, value: Value, version: int) -> None:
    service.assume(
        AssumeRequest(
            actor=task_id,
            task_id=task_id,
            idempotency_key=key(),
            contract=contract,
            expected=value,
            observed_version=version,
        )
    )


def checked_validate(service: Service, task_id: str) -> dict[str, Any]:
    run = validate(service, TaskMutation(actor=task_id, task_id=task_id, idempotency_key=key()))[
        "run"
    ]
    require(
        run["passed"] and run["valid"], "INVALID", f"Demo validation failed for {task_id}: {run}"
    )
    return dict(run)


def write(root: Path, name: str, content: str) -> None:
    (root / name).write_text(content, encoding="utf-8")


def commit(root: Path, message: str) -> None:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=DecisionGuard fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-m",
        message,
    )


def run_demo(destination: Path | None = None) -> dict[str, Any]:
    destination = (destination or Path("artifacts") / f"checkout-{uuid.uuid4().hex[:8]}").resolve()
    require(not destination.exists(), "INVALID", "Demo destination must not already exist")
    destination.mkdir(parents=True)
    root = destination / "repository with spaces"
    root.mkdir()
    git(root, "init", "-b", "main")
    write(root, ".gitignore", "__pycache__/\n")
    write(root, "frontend.py", 'def amount():\n    return "499.00"\n')
    write(
        root,
        "backend.py",
        "from decimal import Decimal\ndef to_provider(value):\n    return int(Decimal(value) * 100)\n",
    )
    write(
        root,
        "test_frontend.py",
        "import unittest\nfrom frontend import amount\nclass Frontend(unittest.TestCase):\n    def test_amount(self):\n        self.assertEqual(amount(), '499.00')\n",
    )
    write(
        root,
        "test_backend.py",
        "import unittest\nfrom backend import to_provider\nclass Backend(unittest.TestCase):\n    def test_adapter(self):\n        self.assertEqual(to_provider('499.00'), 49900)\n",
    )
    write(
        root,
        "test_combined.py",
        "import unittest\nfrom frontend import amount\nfrom backend import to_provider\nclass Combined(unittest.TestCase):\n    def test_checkout(self):\n        self.assertEqual(to_provider(amount()), 49900)\n",
    )
    commit(root, "Initial checkout using decimal major units")
    frontend = destination / "frontend worktree"
    backend = destination / "backend worktree"
    integration = destination / "integration worktree"
    for branch, path in [
        ("frontend", frontend),
        ("backend", backend),
        ("integration", integration),
    ]:
        git(root, "worktree", "add", "-b", branch, str(path))
    directory = initialize(
        root, None, "coordinator", RunnerConfig(argv=[sys.executable, "-m", "unittest", "discover"])
    )
    service = Service(directory)
    config = service.config.model_copy(
        update={
            "task_runners": {
                "frontend": RunnerConfig(argv=[sys.executable, "-m", "unittest", "test_frontend"]),
                "backend": RunnerConfig(argv=[sys.executable, "-m", "unittest", "test_backend"]),
            }
        }
    )
    (directory / "config.json").write_text(config.model_dump_json(indent=2), encoding="utf-8")
    service = Service(directory)
    service.register(
        TaskRequest(
            actor="author",
            task_id="bootstrap",
            idempotency_key=key(),
            worktree=str(root),
            paths=SCOPES,
        )
    )
    establish(service, PUBLIC, MAJOR)
    establish(service, PROVIDER, MINOR)
    for task_id, path, paths, isolated in [
        ("frontend", frontend, ["frontend.py", "test_frontend.py"], False),
        ("backend", backend, ["backend.py", "test_backend.py"], False),
        ("integration", integration, SCOPES, True),
    ]:
        service.register(
            TaskRequest(
                actor=task_id,
                task_id=task_id,
                idempotency_key=key(),
                worktree=str(path),
                paths=paths,
                contracts=[PUBLIC, PROVIDER],
                integration=isolated,
            )
        )
        declare(service, task_id, PUBLIC, MAJOR, 1)
        declare(service, task_id, PROVIDER, MINOR, 1)
    for task_id in ["frontend", "backend", "integration"]:
        checked_validate(service, task_id)
    baseline = gate(service, ["frontend", "backend"], "integration")["receipt"]
    require(baseline["passed"], "INVALID", f"Initial demo gate failed: {baseline['findings']}")
    # The local operator explicitly approves a separate cross-cutting proposal task.
    service.register(
        TaskRequest(
            actor="backend",
            task_id="backend-contract",
            worktree=str(backend),
            paths=SCOPES,
            idempotency_key=key(),
        )
    )
    proposal = service.propose(
        ProposeRequest(
            actor="backend",
            task_id="backend-contract",
            idempotency_key=key(),
            contract=PUBLIC,
            value=MINOR,
            expected_version=1,
            scope=SCOPES,
            rationale="Change public input to integer paise",
        )
    )
    pending = service.poll("frontend", "frontend")["events"]
    require(
        any(e["type"] == "pending_impact" for e in pending), "INVALID", "Pending impact missing"
    )
    pending_gate = gate(service, ["frontend", "backend"], "integration")["receipt"]
    review(service, proposal)
    stale_gate = gate(service, ["frontend", "backend"], "integration")["receipt"]
    write(
        backend,
        "backend.py",
        "from decimal import Decimal\ndef to_provider(value):\n    return int(Decimal(value))\n",
    )
    write(
        backend,
        "test_backend.py",
        "import unittest\nfrom backend import to_provider\nclass Backend(unittest.TestCase):\n    def test_adapter(self):\n        self.assertEqual(to_provider(49900), 49900)\n",
    )
    commit(backend, "Backend accepts public paise")
    git(integration, "merge", "--ff-only", "backend")
    # Directly run the real combined fixture before refreshing knowledge, to demonstrate
    # the application failure independently of DecisionGuard's expected stale rejection.
    from decisionguard.validation.runner import execute

    mismatch = execute(integration, service.config.runner)
    require(
        not mismatch["passed"] and "499 != 49900" in mismatch["output"],
        "INVALID",
        "Combined test did not expose the 100x mismatch",
    )
    delivered = service.poll("frontend", "frontend")["events"]
    service.ack(
        AckRequest(
            actor="frontend",
            task_id="frontend",
            idempotency_key=key(),
            event_id=delivered[-1]["event_id"],
        )
    )
    ack_gate = gate(service, ["frontend", "backend"], "integration")["receipt"]
    require(not ack_gate["passed"], "INVALID", "Acknowledgement incorrectly unblocked gate")
    write(frontend, "frontend.py", "def amount():\n    return 49900\n")
    write(
        frontend,
        "test_frontend.py",
        "import unittest\nfrom frontend import amount\nclass Frontend(unittest.TestCase):\n    def test_amount(self):\n        self.assertEqual(amount(), 49900)\n",
    )
    commit(frontend, "Frontend sends public paise")
    # A true merge combines nonoverlapping frontend/backend edits, with no conflict.
    git(
        integration,
        "-c",
        "user.name=DecisionGuard fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "merge",
        "--no-edit",
        "frontend",
    )
    for task_id in ["frontend", "backend", "integration"]:
        service.refresh(TaskMutation(actor=task_id, task_id=task_id, idempotency_key=key()))
        declare(service, task_id, PUBLIC, MINOR, 2)
        checked_validate(service, task_id)
    repaired = gate(service, ["frontend", "backend"], "integration")["receipt"]
    require(repaired["passed"], "INVALID", f"Repaired combined gate failed: {repaired['findings']}")

    # A second disposable scenario preserves the original API and reviews an explicit adapter.
    alternate_root = destination / "alternative repository"
    git(destination, "clone", "--branch", "main", str(root), str(alternate_root))
    rejection = destination / "rejection integration"
    git(alternate_root, "worktree", "add", "-b", "rejection", str(rejection), "main")
    rejection_state = initialize(alternate_root, None, "coordinator", service.config.runner)
    alternate = Service(rejection_state)
    alternate.register(
        TaskRequest(
            actor="author",
            task_id="bootstrap",
            idempotency_key=key(),
            worktree=str(alternate_root),
            paths=SCOPES,
        )
    )
    establish(alternate, PUBLIC, MAJOR)
    establish(alternate, PROVIDER, MINOR)
    alternate.register(
        TaskRequest(
            actor="integration",
            task_id="integration",
            idempotency_key=key(),
            worktree=str(rejection),
            paths=SCOPES,
            contracts=[PUBLIC, PROVIDER],
            integration=True,
        )
    )
    declare(alternate, "integration", PUBLIC, MAJOR, 1)
    declare(alternate, "integration", PROVIDER, MINOR, 1)
    rejected = alternate.propose(
        ProposeRequest(
            actor="author",
            task_id="bootstrap",
            idempotency_key=key(),
            contract=PUBLIC,
            value=MINOR,
            expected_version=1,
            scope=SCOPES,
            rationale="Alternative change",
        )
    )
    review(alternate, rejected, False)
    alternate.mapping(
        MappingRequest(
            actor="coordinator",
            idempotency_key=key(),
            source=PUBLIC,
            target=PROVIDER,
            source_value=MAJOR,
            target_value=MINOR,
            rationale="Explicit Decimal major-to-integer-paise conversion",
            evidence=["backend.py"],
        )
    )
    checked_validate(alternate, "integration")
    # The alternate branch validates one prepared adapter candidate, not itself as
    # independent integration evidence.
    adapter_gate = gate(alternate, ["integration"])["receipt"]
    require(adapter_gate["passed"], "INVALID", "Compatible adapter scenario failed")
    return envelope(
        simulation=True,
        directory=str(destination),
        baseline_passed=baseline["passed"],
        pending_notice=True,
        pending_blocked=not pending_gate["passed"],
        acceptance_invalidated=not stale_gate["passed"],
        clean_merge=True,
        mismatch_output=mismatch["output"],
        acknowledgement_blocked=not ack_gate["passed"],
        repaired_combined_passed=repaired["passed"],
        rejection_adapter_passed=adapter_gate["passed"],
    )
