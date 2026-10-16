import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest
from conftest import CONTRACT, MAJOR, MINOR, accept, key, proposal

from decisionguard.application.config import state_dir
from decisionguard.application.services import Service
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import AssumeRequest, ReviewRequest, TaskRequest
from decisionguard.git.context import git


def competing_accept(args):
    directory, proposal_id = args
    service = Service(Path(directory))
    (Path(directory) / f"race-{proposal_id}.ready").touch()
    deadline = time.monotonic() + 20
    while len(list(Path(directory).glob("race-*.ready"))) < 2:
        if time.monotonic() > deadline:
            raise TimeoutError("Concurrent review peer did not start")
        time.sleep(0.01)
    try:
        service.review(
            ReviewRequest(
                actor="coordinator",
                idempotency_key=key(),
                proposal_id=proposal_id,
                accept=True,
                expected_version=1,
                rationale="Multiprocess review",
            )
        )
        return "accepted"
    except GuardError as exc:
        return exc.code


def concurrent_registration(args):
    directory, root, identity = args
    service = Service(Path(directory))
    service.register(
        TaskRequest(
            actor=identity,
            task_id=identity,
            worktree=root,
            paths=["code.py"],
            contracts=[CONTRACT],
            idempotency_key=identity,
        )
    )
    return identity


def test_shared_worktree_resolution_and_isolation(project, tmp_path):
    service, root = project
    linked = tmp_path / "linked worktree with spaces"
    git(root, "worktree", "add", "-b", "linked", str(linked))
    assert state_dir(linked) == service.directory
    assert Service(state_dir(linked)).context() == service.context()
    with pytest.raises(GuardError):
        state_dir(root, tmp_path / "split-state")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    git(foreign, "init")
    with pytest.raises(GuardError):
        service.register(
            TaskRequest(
                actor="foreign",
                task_id="foreign",
                worktree=str(foreign),
                paths=["code.py"],
                idempotency_key=key(),
            )
        )
    with pytest.raises(GuardError):
        service.register(
            TaskRequest(
                actor="escape",
                task_id="escape",
                worktree=str(root),
                paths=["../escape"],
                idempotency_key=key(),
            )
        )


def test_real_multiprocess_acceptance_and_writes(project):
    service, root = project
    first = proposal(service, MINOR)
    second = proposal(service, MAJOR)
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=2, mp_context=ctx) as pool:
        outcomes = list(
            pool.map(
                competing_accept,
                [(str(service.directory), p["proposal"]["proposal_id"]) for p in [first, second]],
            )
        )
    assert sorted(outcomes) == ["VERSION_CONFLICT", "accepted"]
    assert service.context()["revision"] == 2
    with ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        registered = list(
            pool.map(
                concurrent_registration,
                [(str(service.directory), str(root), f"task-{i}") for i in range(8)],
            )
        )
    assert len(registered) == 8
    assert all(service.context(identity)["task"] for identity in registered)


def test_independent_boundary_and_unknown_schema(project):
    from decisionguard.domain.models import Contract, ProposeRequest, Value

    service, root = project
    other = Contract(boundary="provider.request", key="amount.unit")
    change = service.propose(
        ProposeRequest(
            actor="worker",
            task_id="worker",
            idempotency_key=key(),
            contract=other,
            value=MINOR,
            expected_version=0,
            scope=["code.py"],
            rationale="Independent provider",
        )
    )
    accept(service, change)
    assert not service.conflicts(["worker"])["findings"]
    schema = Contract(boundary="api.response", key="schema")
    for version, fingerprint in [(0, "sha256:a"), (1, "sha256:b")]:
        change = service.propose(
            ProposeRequest(
                actor="worker",
                task_id="worker",
                idempotency_key=key(),
                contract=schema,
                value=Value(kind="schema", value=fingerprint),
                expected_version=version,
                scope=["code.py"],
                rationale="Schema fixture",
            )
        )
        accept(service, change)
        if version == 0:
            service.assume(
                AssumeRequest(
                    actor="worker",
                    task_id="worker",
                    idempotency_key=key(),
                    contract=schema,
                    expected=Value(kind="schema", value=fingerprint),
                    observed_version=1,
                )
            )
    assert any(
        f["kind"] == "unknown_compatibility" for f in service.conflicts(["worker"])["findings"]
    )
