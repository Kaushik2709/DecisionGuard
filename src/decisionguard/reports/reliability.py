"""Disposable, real-process recovery and performance workloads. No user state is opened."""

import math
import multiprocessing
import os
import sqlite3
import sys
import time
import tracemalloc
import uuid
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from decisionguard.application.config import initialize
from decisionguard.application.operations import backup, restore_backup
from decisionguard.application.services import Service, envelope
from decisionguard.application.validation import gate, validate
from decisionguard.domain.errors import GuardError, require
from decisionguard.domain.models import (
    AssumeRequest,
    Contract,
    Mutation,
    ProposeRequest,
    ReviewRequest,
    RunnerConfig,
    TaskMutation,
    TaskRequest,
    Value,
)
from decisionguard.git.context import git
from decisionguard.storage.sqlite import get, heads, put
from decisionguard.validation.snapshot import stable_capture

CONTRACT = Contract(boundary="fixture", key="amount.unit")
MAJOR = Value(kind="money_unit", value="INR.major.decimal-string")
MINOR = Value(kind="money_unit", value="INR.minor.integer")


def _key() -> str:
    return uuid.uuid4().hex


def _fixture(destination: Path, workers: int = 1, *, use_git: bool = True) -> tuple[Service, Path]:
    destination = destination.resolve()
    require(not destination.exists(), "INVALID", "Choose a new disposable destination")
    destination.mkdir(parents=True)
    root = destination / "repository"
    root.mkdir()
    (root / "code.py").write_text("amount = '499.00'\n", encoding="utf-8")
    (root / "check.py").write_text(
        "from code import amount\nassert int(float(amount)*100)==49900\n", encoding="utf-8"
    )
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    if use_git:
        git(root, "init", "-b", "main")
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=DecisionGuard fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "Disposable reliability fixture",
        )
    directory = initialize(
        root,
        None if use_git else destination / "state",
        "reviewer",
        RunnerConfig(argv=[sys.executable, "-B", "check.py"]),
    )
    service = Service(directory)
    service.register(
        TaskRequest(
            actor="author",
            task_id="author",
            worktree=str(root),
            paths=["code.py", "check.py"],
            idempotency_key=_key(),
        )
    )
    item = _propose(service, MAJOR, 0)
    service.review(_review(item))
    for index in range(workers):
        identity = f"worker-{index}"
        path = root
        if use_git:
            path = destination / identity
            git(root, "worktree", "add", "-b", identity, str(path))
        service.register(
            TaskRequest(
                actor=identity,
                task_id=identity,
                worktree=str(path),
                paths=["code.py", "check.py"],
                contracts=[CONTRACT],
                idempotency_key=_key(),
            )
        )
        service.assume(
            AssumeRequest(
                actor=identity,
                task_id=identity,
                contract=CONTRACT,
                expected=MAJOR,
                observed_version=1,
                idempotency_key=_key(),
            )
        )
    return service, root


def _propose(service: Service, value: Value, version: int) -> dict[str, Any]:
    return dict(
        service.propose(
            ProposeRequest(
                actor="author",
                task_id="author",
                contract=CONTRACT,
                value=value,
                expected_version=version,
                scope=["code.py", "check.py"],
                rationale="Disposable reliability workload",
                idempotency_key=_key(),
            )
        )["proposal"]
    )


def _review(proposal: dict[str, Any]) -> ReviewRequest:
    return ReviewRequest(
        actor="reviewer",
        proposal_id=proposal["proposal_id"],
        accept=True,
        expected_version=proposal["expected_version"],
        rationale="Explicit fixture review",
        idempotency_key=_key(),
    )


def _killable_review(directory: str, request: str, phase: str, ready: Any) -> None:
    service = Service(Path(directory))
    if phase == "before_commit":
        original = service.store.transaction

        @contextmanager
        def paused() -> Any:
            with original() as db:
                yield db
                ready.set()
                time.sleep(60)

        service.store.transaction = paused  # type: ignore[method-assign]
    service.review(ReviewRequest.model_validate_json(request))
    ready.set()
    time.sleep(60)


def _kill_review(directory: Path, request: ReviewRequest, phase: str) -> None:
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    child = context.Process(
        target=_killable_review, args=(str(directory), request.model_dump_json(), phase, ready)
    )
    child.start()
    try:
        require(ready.wait(20), "OPERATIONAL", "Child did not reach the intended crash point")
        child.kill()
        child.join(10)
        require(not child.is_alive(), "OPERATIONAL", "Fixture child did not stop")
    finally:
        if child.is_alive():
            child.kill()
            child.join(10)


def _capacity_failure(service: Service) -> dict[str, Any]:
    def action(db: sqlite3.Connection) -> dict[str, Any]:
        pages = db.execute("PRAGMA page_count").fetchone()[0]
        db.execute(f"PRAGMA max_page_count={pages}")
        put(db, "capacity_probe", "probe", {"payload": "x" * (1024 * 1024)})
        return {"unexpected": "write fit"}

    failed = False
    try:
        service.mutate(
            "capacity_drill", Mutation(actor="reviewer", idempotency_key="capacity"), action
        )
    except sqlite3.Error as exc:
        failed = getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_FULL
    with service.store.connect() as db:
        absent = db.execute("SELECT 1 FROM entities WHERE kind='capacity_probe'").fetchone() is None
        no_retry = db.execute("SELECT 1 FROM retries WHERE key='capacity'").fetchone() is None
        intact = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    require(
        failed and absent and no_retry and intact,
        "OPERATIONAL",
        "Capacity rollback invariant failed",
    )
    return {
        "sqlite_full_observed": failed,
        "partial_record_absent": absent,
        "retry_absent": no_retry,
        "integrity_ok": intact,
        "physical_disk_full": False,
    }


def recovery_drill(destination: Path) -> dict[str, Any]:
    service, _ = _fixture(destination)
    directory = service.directory
    try:
        initial = validate(
            service, TaskMutation(actor="worker-0", task_id="worker-0", idempotency_key=_key())
        )
        require(initial["run"]["passed"], "OPERATIONAL", "Initial runner failed")
        first = _review(_propose(service, MINOR, 1))
        _kill_review(directory, first, "before_commit")
        with service.store.connect() as db:
            rollback_ok = (
                heads(db)[CONTRACT.identity]["version"] == 1
                and get(db, "proposal", first.proposal_id)["status"] == "pending"
                and get(db, "run", initial["run"]["run_id"])["valid"]
            )
        require(rollback_ok, "OPERATIONAL", "Killed transaction was partially committed")
        service.review(first)
        second = _review(_propose(service, MAJOR, 2))
        _kill_review(directory, second, "after_commit")
        with service.store.connect() as db:
            epoch = db.execute("SELECT value FROM meta WHERE key='state_epoch'").fetchone()[0]
        retry = service.review(second)
        with service.store.connect() as db:
            replay_ok = (
                heads(db)[CONTRACT.identity]["version"] == 3
                and db.execute("SELECT value FROM meta WHERE key='state_epoch'").fetchone()[0]
                == epoch
            )
        require(replay_ok, "OPERATIONAL", "Lost-response retry duplicated state changes")
        capacity = _capacity_failure(service)
        service.refresh(TaskMutation(actor="worker-0", task_id="worker-0", idempotency_key=_key()))
        validate(
            service, TaskMutation(actor="worker-0", task_id="worker-0", idempotency_key=_key())
        )
        require(
            gate(service, ["worker-0"])["receipt"]["passed"],
            "OPERATIONAL",
            "Fresh runner did not clear fixture",
        )
        saved = destination.resolve() / "recovery-backup.db"
        backup(service, saved)
        service.close()
        restore_backup(directory, saved, sessions_stopped=True)
        current = Service(directory)
        try:
            blocked = not gate(current, ["worker-0"])["receipt"]["passed"]
            with current.store.connect() as db:
                history = heads(db)[CONTRACT.identity]["version"] == 3
        finally:
            current.close()
        require(blocked and history, "OPERATIONAL", "Restore resurrected evidence or lost history")
        return envelope(
            fixture_only=True,
            killed_before_commit_rolled_back=rollback_ok,
            killed_after_commit_retry_unchanged=replay_ok,
            retry_result_recorded=bool(retry),
            restored_history_preserved=history,
            restored_gate_blocked=blocked,
            capacity_limit=capacity,
            destination=str(destination.resolve()),
        )
    finally:
        service.close()


def filesystem_full_drill(destination: Path) -> dict[str, Any]:
    """Only run on an explicitly bounded small filesystem, e.g. disposable Docker tmpfs."""
    require(hasattr(os, "statvfs"), "INVALID", "Bounded filesystem drill requires POSIX statvfs")
    stat = cast(Any, os).statvfs(destination.parent)
    capacity = stat.f_blocks * stat.f_frsize
    require(
        0 < capacity <= 16 * 1024 * 1024,
        "INVALID",
        "Use a disposable filesystem no larger than 16 MiB",
    )
    service, _ = _fixture(destination, use_git=False)
    filler = destination / "fixture-filler.bin"
    try:
        free = cast(Any, os).statvfs(destination).f_bavail * stat.f_frsize
        with filler.open("xb") as stream:
            remaining = max(0, free - 262144)
            while remaining:
                chunk = min(remaining, 65536)
                stream.write(b"x" * chunk)
                remaining -= chunk
        failed = False
        try:

            def action(db: sqlite3.Connection) -> dict[str, Any]:
                put(db, "disk_probe", "probe", {"payload": "x" * 1024 * 1024})
                return {"unexpected": True}

            service.mutate(
                "filesystem_full", Mutation(actor="reviewer", idempotency_key="disk-full"), action
            )
        except sqlite3.Error as exc:
            failed = getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_FULL
        finally:
            filler.unlink(missing_ok=True)
        with service.store.connect() as db:
            intact = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            absent = db.execute("SELECT 1 FROM entities WHERE kind='disk_probe'").fetchone() is None
            retry_absent = (
                db.execute("SELECT 1 FROM retries WHERE key='disk-full'").fetchone() is None
            )
            history = heads(db)[CONTRACT.identity]["version"] == 1
        # Confirm subsequent real application writes work after capacity returns.
        service.refresh(TaskMutation(actor="worker-0", task_id="worker-0", idempotency_key=_key()))
        require(
            failed and intact and absent and retry_absent and history,
            "OPERATIONAL",
            "Filesystem-full recovery invariant failed",
        )
        return envelope(
            fixture_only=True,
            bounded_filesystem_bytes=capacity,
            filesystem_full_observed=failed,
            integrity_ok=intact,
            partial_record_absent=absent,
            retry_absent=retry_absent,
            history_preserved=history,
            subsequent_mutation_passed=True,
        )
    finally:
        filler.unlink(missing_ok=True)
        service.close()


def _stats(samples: list[float]) -> dict[str, Any]:
    ordered = sorted(samples)
    return {
        "samples": len(ordered),
        "p50_ms": ordered[math.ceil(len(ordered) * 0.5) - 1] if ordered else None,
        "p95_ms": ordered[math.ceil(len(ordered) * 0.95) - 1] if ordered else None,
    }


def _soak_worker(directory: str, identity: str, seconds: float) -> dict[str, Any]:
    service = Service(Path(directory))
    tracemalloc.start()
    started = time.monotonic()
    samples: dict[str, list[float]] = {k: [] for k in ("validation", "gate", "snapshot")}
    counts = {"iterations": 0, "passed_gates": 0, "state_changed_gates": 0, "busy": 0, "errors": 0}
    try:
        while time.monotonic() - started < seconds:
            request = TaskMutation(actor=identity, task_id=identity, idempotency_key=_key())
            try:
                begin = time.perf_counter()
                outcome = validate(service, request)["run"]
                samples["validation"].append((time.perf_counter() - begin) * 1000)
                require(
                    outcome["passed"] and outcome["valid"],
                    "OPERATIONAL",
                    "Fixture validation failed",
                )
                begin = time.perf_counter()
                receipt = gate(service, [identity])["receipt"]
                samples["gate"].append((time.perf_counter() - begin) * 1000)
                kinds = {f["kind"] for f in receipt["findings"]}
                if receipt["passed"]:
                    counts["passed_gates"] += 1
                elif kinds <= {"state_changed"}:
                    counts["state_changed_gates"] += 1
                else:
                    counts["errors"] += 1
                with service.store.connect() as db:
                    task = get(db, "task", identity)
                begin = time.perf_counter()
                stable_capture(
                    Path(task["worktree"]),
                    service.config.exclusions,
                    service.directory,
                    service.config.limits,
                )
                samples["snapshot"].append((time.perf_counter() - begin) * 1000)
            except GuardError as exc:
                counts["busy" if exc.code == "BUSY" else "errors"] += 1
            counts["iterations"] += 1
            if any(len(values) >= 100000 for values in samples.values()):
                break
        _, peak = tracemalloc.get_traced_memory()
        return {
            **counts,
            "latencies": samples,
            "python_tracemalloc_peak_bytes": peak,
            "elapsed_seconds": time.monotonic() - started,
        }
    finally:
        tracemalloc.stop()
        service.close()


def soak(
    destination: Path, *, seconds: float = 30, workers: int = 2, history: int = 1000
) -> dict[str, Any]:
    require(
        math.isfinite(seconds) and 0 < seconds <= 28800,
        "INVALID",
        "Duration must be in (0,28800] seconds",
    )
    require(
        2 <= workers <= 4 and 0 <= history <= 100000,
        "INVALID",
        "Use 2-4 workers and at most 100000 history events",
    )
    service, _ = _fixture(destination, workers)
    try:
        with service.store.transaction() as db:
            for index in range(history):
                service.emit(
                    db, f"worker-{index % workers}", "fixture_history", {"sequence": index}
                )
        before = _sizes(service.directory)
        started = time.monotonic()
        with ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn")
        ) as pool:
            jobs = [
                pool.submit(_soak_worker, str(service.directory), f"worker-{i}", seconds)
                for i in range(workers)
            ]
            outcomes = [job.result(timeout=seconds + 120) for job in jobs]
        elapsed = time.monotonic() - started
        quiescent = {
            f"worker-{i}": gate(service, [f"worker-{i}"])["receipt"]["passed"]
            for i in range(workers)
        }
        after = _sizes(service.directory)
        return envelope(
            fixture_only=True,
            destination=str(destination.resolve()),
            requested_seconds=seconds,
            elapsed_seconds=elapsed,
            workers=workers,
            seeded_history_events=history,
            full_8_hour_soak_completed=seconds >= 28800
            and all(o["elapsed_seconds"] >= 28800 for o in outcomes),
            workload="real linked worktrees; validate, single-task gate and source snapshot; fixed Python assertion",
            worker_results=[{k: v for k, v in o.items() if k != "latencies"} for o in outcomes],
            latencies={
                name: _stats([s for o in outcomes for s in o["latencies"][name]])
                for name in ("validation", "gate", "snapshot")
            },
            state_bytes_before=before,
            state_bytes_after=after,
            process_rss_peak_bytes=None,
            memory_scope="Python tracemalloc per worker; native SQLite/OS allocations not measured",
            quiescent_gates=quiescent,
            passed=all(
                o["errors"] == 0 and o["passed_gates"] + o["state_changed_gates"] > 0
                for o in outcomes
            )
            and all(quiescent.values()),
            production_reliability_established=False,
        )
    finally:
        service.close()


def _sizes(directory: Path) -> dict[str, int]:
    return {
        name: (directory / name).stat().st_size if (directory / name).exists() else 0
        for name in ("state.db", "state.db-wal", "state.db-shm")
    }
