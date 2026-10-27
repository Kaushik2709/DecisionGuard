"""Reviewable, resumable local onboarding and fresh read-only task guidance."""

from pathlib import Path
from typing import Any

from decisionguard.application.config import initialize, load_config, state_dir
from decisionguard.application.services import Service, digest, envelope
from decisionguard.application.validation import gate
from decisionguard.domain.errors import require
from decisionguard.domain.models import TaskRequest
from decisionguard.domain.onboarding import ProjectSetup
from decisionguard.git.context import common_dir, repository_root, safe_path


def setup_project(
    root: Path, state: Path | None, request: ProjectSetup, *, apply: bool = False
) -> dict[str, Any]:
    root = root.resolve()
    require(root.is_dir(), "INVALID", "Project root does not exist")
    common = common_dir(root)
    if common:
        root = repository_root(root)
    directory = state_dir(root, state)
    existing = (directory / "config.json").is_file()
    if existing:
        config = load_config(directory)
        require(
            config.root == str(root) and config.common_dir == (str(common) if common else None),
            "FORBIDDEN",
            "Existing configuration belongs to a different root",
        )
        require(
            request.coordinator in config.coordinators,
            "FORBIDDEN",
            "Configured coordinator required",
        )
        require(
            config.runner == request.runner,
            "CONFIG_CHANGED",
            "Setup never overwrites an existing runner",
        )
    tasks = []
    for task in request.tasks:
        worktree = (root / task.worktree).resolve()
        require(worktree.is_dir(), "INVALID", "Create the requested worktree before setup")
        require(
            (
                common is not None
                and common_dir(worktree) == common
                and repository_root(worktree) == worktree
            )
            or (common is None and worktree == root),
            "FORBIDDEN",
            "Setup task must use this project's worktree root",
        )
        require(
            not task.integration or (common is not None and worktree != root),
            "INVALID",
            "Integration needs a separate linked worktree",
        )
        for path in task.paths:
            safe_path(worktree, path)
        safe_path(worktree, request.runner.cwd)
        tasks.append(task.model_copy(update={"worktree": str(worktree)}))
    integration_roots = {t.worktree for t in tasks if t.integration}
    require(
        not integration_roots & {t.worktree for t in tasks if not t.integration},
        "INVALID",
        "Integration cannot share an implementation worktree",
    )
    fingerprint = digest(
        {
            "root": str(root),
            "state": str(directory),
            "request": request.model_dump(),
            "tasks": [t.model_dump() for t in tasks],
        }
    )
    result = envelope(
        preview_only=not apply,
        plan_sha256=fingerprint,
        existing_configuration=existing,
        state=str(directory),
        tasks=[t.model_dump() for t in tasks],
        warnings=[
            "Scope '.' covers the whole fixture/worktree; review whether narrower paths suffice"
        ]
        if any("." in t.paths for t in tasks)
        else [],
        next_steps=[
            "Review and explicitly publish/accept contracts if needed",
            "Declare implementation assumptions; acknowledgement is not validation",
            "Run next to inspect current coverage and evidence requirements",
        ],
        contracts_accepted=0,
        validation_executed=False,
    )
    if not apply:
        return result
    if not existing:
        initialize(root, state, request.coordinator, request.runner)
    local = Service(directory)
    try:
        local.authorize(request.coordinator, coordinator=True)
        registered = []
        for task in tasks:
            registered.append(
                local.register(
                    TaskRequest(
                        **task.model_dump(),
                        idempotency_key="setup-"
                        + digest({"plan": fingerprint, "task": task.task_id}),
                    )
                )["task"]["task_id"]
            )
        result["registered_tasks"] = registered
    finally:
        local.close()
    return result


def next_actions(
    service: Service, task_ids: list[str], integration_task: str | None = None
) -> dict[str, Any]:
    require(service.session_actor is None, "FORBIDDEN", "Guidance is a local operator operation")
    assessment = gate(service, task_ids, integration_task, record_receipt=False)["receipt"]
    priorities = {
        "unapproved_scope": 0,
        "pending_impact": 10,
        "confirmed_conflict": 20,
        "unknown_compatibility": 20,
        "stale_dependencies": 30,
        "incomplete_coverage": 40,
        "unknown_coverage": 40,
        "out_of_scope_change": 40,
        "missing_or_stale_evidence": 80,
        "missing_combined_validation": 90,
        "combined_source_mismatch": 90,
    }
    ordered = sorted(
        assessment["findings"],
        key=lambda f: (priorities.get(f["kind"], 50), f["task_id"], f.get("contract") or ""),
    )
    return envelope(
        read_only=True,
        receipt_persisted=False,
        scope_passed=assessment["passed"],
        integration_checked=assessment["integration_checked"],
        findings=ordered,
        next_action=ordered[0]["next_action"]
        if ordered
        else "Declared scope is current; recheck the gate before integration",
        validation_executed=False,
        decisions_accepted=0,
    )
