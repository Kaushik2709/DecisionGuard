import uuid
from pathlib import Path
from typing import Any

from decisionguard.application.config import load_config
from decisionguard.application.services import Service, digest, envelope, now
from decisionguard.domain.errors import require
from decisionguard.domain.models import TaskMutation
from decisionguard.git.context import scoped_path
from decisionguard.storage.sqlite import get, heads, put, revision
from decisionguard.validation.runner import execute
from decisionguard.validation.snapshot import changed_paths, stable_capture


def validate(service: Service, request: TaskMutation) -> dict[str, Any]:
    require(
        service.session_actor is None, "FORBIDDEN", "Only explicit local CLI can run validation"
    )
    service.authorize(request.actor)

    # Reserve a durable run ID before executing outside the database transaction.
    # A retry never reruns a command whose effects may already have occurred.
    def reserve(db: Any) -> dict[str, Any]:
        task = service.task(db, request.task_id, request.actor)
        require(task["scope_approved"], "FORBIDDEN", "Task scope awaits coordinator approval")
        active = heads(db)
        require(
            all(active[k]["version"] == v for k, v in task["dependencies"].items()),
            "VERSION_CONFLICT",
            "Refresh stale dependencies before validation",
        )
        run_id = str(uuid.uuid4())
        task["run_sequence"] += 1
        task["latest_run_id"] = run_id
        put(db, "task", request.task_id, task)
        run = {
            "run_id": run_id,
            "sequence": task["run_sequence"],
            "evidence_generation": task["evidence_generation"],
            "task_id": request.task_id,
            "status": "running",
            "valid": False,
            "passed": False,
            "timestamp": now(),
            "dependencies": task["dependencies"],
            "revision": revision(db),
            "config_digest": digest(service.config.model_dump()),
        }
        put(db, "run", run_id, run)
        return {"run_id": run_id}

    reservation = service.mutate("validate", request, reserve)
    run_id = reservation["run_id"]
    with service.store.connect() as db:
        run = get(db, "run", run_id)
        task = service.task(db, request.task_id, request.actor)
    if run["status"] != "running":
        return envelope(run=run)
    # Claim execution once. An interrupted executing run is deliberately unusable;
    # use a new idempotency key after investigating, rather than silently rerunning it.
    with service.store.transaction() as db:
        run = get(db, "run", run_id)
        if run["status"] != "running":
            return envelope(run=run)
        run["status"] = "executing"
        put(db, "run", run_id, run)
    root = Path(task["worktree"])
    try:
        config = load_config(service.directory)
        require(
            digest(config.model_dump()) == run["config_digest"],
            "CONFIG_CHANGED",
            "Configuration changed",
        )
        before = stable_capture(root, config.exclusions, service.directory, config.limits)
        outcome = execute(root, config.task_runners.get(request.task_id, config.runner))
        after = stable_capture(root, config.exclusions, service.directory, config.limits)
        same_source = before == after
        same_config = digest(load_config(service.directory).model_dump()) == run["config_digest"]
        run.update(outcome)
        run.update(source=before, status="finished")
        with service.store.transaction() as db:
            current = service.task(db, request.task_id)
            active = heads(db)
            same_decisions = all(active[k]["version"] == v for k, v in run["dependencies"].items())
            # Mapping changes also affect the meaning of evidence, so bind the project revision.
            fresh = (
                same_source
                and same_config
                and same_decisions
                and revision(db) == run["revision"]
                and current["dependencies"] == run["dependencies"]
                and current["evidence_generation"] == run["evidence_generation"]
                and current["latest_run_id"] == run_id
            )
            run["valid"] = fresh
            run["freshness"] = {
                "source": same_source,
                "config": same_config,
                "decisions": same_decisions,
                "revision": revision(db) == run["revision"],
            }
            put(db, "run", run_id, run)
    except Exception as exc:
        run.update(
            status="error",
            valid=False,
            passed=False,
            error={"code": getattr(exc, "code", "OPERATIONAL"), "message": str(exc)},
        )
        with service.store.transaction() as db:
            put(db, "run", run_id, run)
    return envelope(run=run)


def gate(
    service: Service,
    task_ids: list[str],
    integration_task: str | None = None,
    *,
    record_receipt: bool = True,
) -> dict[str, Any]:
    require(
        bool(task_ids) and len(task_ids) <= 100 and len(set(task_ids)) == len(task_ids),
        "INVALID",
        "Select 1–100 distinct tasks",
    )
    selected = task_ids + (
        [integration_task] if integration_task and integration_task not in task_ids else []
    )
    require(integration_task not in task_ids, "INVALID", "Integration must be a distinct task")
    snapshots: dict[str, dict[str, Any]] = {}
    changed: dict[str, list[str]] = {}
    config = load_config(service.directory)
    with service.store.connect() as db:
        tasks = {identity: service.task(db, identity) for identity in selected}
    if integration_task:
        require(
            all(
                Path(tasks[identity]["worktree"]).resolve()
                != Path(tasks[integration_task]["worktree"]).resolve()
                for identity in task_ids
            ),
            "INVALID",
            "Integration requires a distinct worktree from every selected task",
        )
    for identity, task in tasks.items():
        root = Path(task["worktree"])
        snapshots[identity] = stable_capture(
            root, config.exclusions, service.directory, config.limits
        )
        changed[identity] = changed_paths(
            root, task.get("baseline_commit"), config.limits, config.exclusions, service.directory
        )

    with service.store.connect() as db:
        db.execute("BEGIN")
        observed_epoch = db.execute("SELECT value FROM meta WHERE key='state_epoch'").fetchone()[0]
        observed_revision = revision(db)
        findings = service.findings(db, selected)
        active = heads(db)
        evidence_runs: dict[str, str] = {}

        def add(kind: str, identity: str, action: str, evidence: Any = None) -> None:
            findings.append(
                {
                    "kind": kind,
                    "task_id": identity,
                    "contract": None,
                    "expected": None,
                    "active": None,
                    "rule": kind,
                    "evidence": evidence or [],
                    "next_action": action,
                }
            )

        for identity, task in tasks.items():
            current = service.task(db, identity)
            if current != task:
                add("stale_dependencies", identity, "Task changed during gate; retry")
            if not task["scope_approved"]:
                add("unapproved_scope", identity, "Coordinator must approve task scope")
            if not task["dependencies"]:
                add(
                    "incomplete_coverage",
                    identity,
                    "Declare at least one dependency for the gate scope",
                )
            coverage = [p for k in task["dependencies"] for p in active[k]["scope"]]
            for path in set(task["paths"] + changed[identity]):
                full = (Path(task["worktree"]) / path).resolve()
                if full.is_relative_to(service.directory):
                    continue
                if any(scoped_path(path, x) for x in config.exclusions):
                    continue
                if not any(scoped_path(path, scope) for scope in task["paths"]):
                    add(
                        "out_of_scope_change",
                        identity,
                        "Request coordinator approval for changed task scope",
                        [path],
                    )
                if not any(scoped_path(path, scope) for scope in coverage):
                    add(
                        "unknown_coverage",
                        identity,
                        "Review contract scope for this changed/selected path",
                        [path],
                    )
            latest = get(db, "run", task["latest_run_id"]) if task["latest_run_id"] else None
            candidates = [
                run
                for run in ([latest] if latest else [])
                if run["task_id"] == identity
                and run["valid"]
                and run["passed"]
                and run["status"] == "finished"
                and run["dependencies"] == task["dependencies"]
                and run["revision"] == observed_revision
                and run["config_digest"] == digest(config.model_dump())
                and run.get("source") == snapshots[identity]
                and run["evidence_generation"] == task["evidence_generation"]
                and run["sequence"] == task["run_sequence"]
            ]
            if not candidates:
                add(
                    "missing_or_stale_evidence",
                    identity,
                    "Run configured local validation on current source",
                )
            else:
                evidence_runs[identity] = candidates[0]["run_id"]

        if integration_task:
            integration = tasks[integration_task]
            require(
                integration["integration"],
                "INVALID",
                "Selected integration task is not isolated integration",
            )
            union = {
                key: value
                for identity in task_ids
                for key, value in tasks[identity]["dependencies"].items()
            }
            if any(integration["dependencies"].get(k) != v for k, v in union.items()):
                add(
                    "incomplete_coverage",
                    integration_task,
                    "Integration must depend on all selected contracts",
                )
            for identity in task_ids:
                task = tasks[identity]
                expected_files = {
                    name: value
                    for name, value in snapshots[identity]["files"].items()
                    if value != "DELETED" and any(scoped_path(name, p) for p in task["paths"])
                }
                combined_files = {
                    name: value
                    for name, value in snapshots[integration_task]["files"].items()
                    if value != "DELETED" and any(scoped_path(name, p) for p in task["paths"])
                }
                if expected_files != combined_files:
                    add(
                        "combined_source_mismatch",
                        integration_task,
                        "Prepare combined worktree with current selected implementations",
                        [identity],
                    )
        elif len(task_ids) > 1:
            add("missing_combined_validation", task_ids[0], "Select an isolated integration task")

    # Expensive filesystem work never holds the database writer lock.
    for identity, task in tasks.items():
        if (
            stable_capture(
                Path(task["worktree"]), config.exclusions, service.directory, config.limits
            )
            != snapshots[identity]
        ):
            add("source_changed", identity, "Source changed during gate; retry")
        if (
            changed_paths(
                Path(task["worktree"]),
                task.get("baseline_commit"),
                config.limits,
                config.exclusions,
                service.directory,
            )
            != changed[identity]
        ):
            add("source_changed", identity, "Changed-path coverage moved during gate; retry")
    if digest(load_config(service.directory).model_dump()) != digest(config.model_dump()):
        add("config_changed", selected[0], "Configuration changed during gate; retry")
    with service.store.transaction() as db:
        if (
            db.execute("SELECT value FROM meta WHERE key='state_epoch'").fetchone()[0]
            != observed_epoch
        ):
            add("state_changed", selected[0], "State changed during gate; retry")
        # Configuration is a small local file, not a source tree capture.
        if digest(load_config(service.directory).model_dump()) != digest(config.model_dump()):
            add("config_changed", selected[0], "Configuration changed during gate; retry")
        receipt: dict[str, Any] = {
            "receipt_id": str(uuid.uuid4()),
            "passed": not findings,
            "scope": {"tasks": task_ids, "integration_task": integration_task},
            "revision": observed_revision,
            "source_digests": {k: v["digest"] for k, v in snapshots.items()},
            "config_digest": digest(config.model_dump()),
            "evidence_runs": evidence_runs,
            "timestamp": now(),
            "findings": findings,
            "integration_checked": integration_task is not None,
        }
        if record_receipt:
            put(db, "receipt", receipt["receipt_id"], receipt)
        return envelope(receipt=receipt)
