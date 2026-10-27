import hashlib
import json
import sqlite3
import uuid
import weakref
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from decisionguard.application.config import load_config
from decisionguard.domain.compatibility import compare
from decisionguard.domain.errors import require
from decisionguard.domain.models import (
    AckRequest,
    AssumeRequest,
    MappingRequest,
    Mutation,
    ProposeRequest,
    ReviewRequest,
    ScopeApproval,
    TaskMutation,
    TaskRequest,
    Value,
)
from decisionguard.git.context import common_dir, git, repository_root, safe_path
from decisionguard.storage.locking import exclusive_lock
from decisionguard.storage.sqlite import Store, all_entities, dumps, get, heads, put, revision


def now() -> str:
    return datetime.now(UTC).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def envelope(**data: Any) -> dict[str, Any]:
    return {"schema_version": 1, **data}


class Service:
    def __init__(self, directory: Path, session_actor: str | None = None):
        self.directory = directory.resolve()
        self.config = load_config(self.directory)
        lease = exclusive_lock(self.directory / "activity.lock", shared=True)
        lease.__enter__()
        self._release = weakref.finalize(self, lease.__exit__, None, None, None)
        try:
            self.store = Store(self.directory / "state.db", self.config.project)
        except BaseException:
            self.close()
            raise
        self.session_actor = session_actor

    def close(self) -> None:
        self._release()

    def authorize(self, actor: str, *, coordinator: bool = False) -> None:
        require(self._release.alive, "INVALID", "Service session is closed")
        current = load_config(self.directory)
        require(
            (current.project, current.root, current.common_dir)
            == (self.config.project, self.config.root, self.config.common_dir),
            "CONFIG_CHANGED",
            "Project identity changed; restart with verified configuration",
        )
        self.config = current
        require(
            self.session_actor is None or actor == self.session_actor,
            "FORBIDDEN",
            "Actor differs from server-bound session",
        )
        if coordinator:
            require(
                actor in self.config.coordinators, "FORBIDDEN", "Coordinator capability required"
            )

    def task(
        self, db: sqlite3.Connection, task_id: str, actor: str | None = None
    ) -> dict[str, Any]:
        task = get(db, "task", task_id)
        require(not task.get("archived", False), "INVALID", "Task is archived; restore it first")
        if actor is not None:
            self.authorize(actor)
            require(task["actor"] == actor, "FORBIDDEN", "Task belongs to another actor")
        self.worktree(Path(task["worktree"]))
        return task

    def worktree(self, root: Path) -> None:
        require(root.is_dir(), "INVALID", "Worktree does not exist")
        if self.config.common_dir:
            require(
                common_dir(root) == Path(self.config.common_dir), "FORBIDDEN", "Foreign repository"
            )
            require(
                repository_root(root) == root.resolve(),
                "INVALID",
                "Register a worktree root, not a subdirectory",
            )
        else:
            require(
                root.resolve() == Path(self.config.root).resolve(),
                "FORBIDDEN",
                "Foreign project root",
            )

    def mutate(
        self,
        operation: str,
        request: Mutation,
        action: Callable[[sqlite3.Connection], dict[str, Any]],
    ) -> dict[str, Any]:
        self.authorize(request.actor)
        fingerprint = digest({"operation": operation, "request": request.model_dump()})
        with self.store.transaction() as db:
            self.authorize(
                request.actor,
                coordinator=operation
                in {"review_proposal", "review_mapping", "approve_task_scope", "import_metadata"},
            )
            old = db.execute(
                "SELECT fingerprint,result FROM retries WHERE actor=? AND key=?",
                (request.actor, request.idempotency_key),
            ).fetchone()
            if old:
                require(old[0] == fingerprint, "IDEMPOTENCY_CONFLICT", "Retry payload differs")
                return dict(json.loads(old[1]))
            result = envelope(**action(db))
            db.execute(
                "INSERT INTO retries VALUES(?,?,?,?)",
                (request.actor, request.idempotency_key, fingerprint, dumps(result)),
            )
            return result

    def emit(
        self, db: sqlite3.Connection, task_id: str, event_type: str, data: dict[str, Any]
    ) -> None:
        notice_key = digest({"task": task_id, "type": event_type, "data": data})
        db.execute(
            "INSERT INTO events(task,body) SELECT ?,? WHERE NOT EXISTS "
            "(SELECT 1 FROM events WHERE task=? AND json_extract(body,'$.notice_key')=?)",
            (
                task_id,
                dumps({"type": event_type, "timestamp": now(), "notice_key": notice_key, **data}),
                task_id,
                notice_key,
            ),
        )

    def relevant(self, task: dict[str, Any], key: str, scope: list[str]) -> bool:
        return key in task["dependencies"] or any(
            self.overlap(a, b) for a in task["paths"] for b in scope
        )

    def proposal_scope(self, db: sqlite3.Connection, proposal: dict[str, Any]) -> list[str]:
        key = f"{proposal['contract']['boundary']}::{proposal['contract']['key']}"
        # The predecessor scope matters even when the proposal moves or deletes a boundary.
        row = db.execute(
            "SELECT body FROM versions WHERE contract=? AND version=?",
            (key, proposal["expected_version"]),
        ).fetchone()
        current = db.execute(
            "SELECT v.body FROM heads h JOIN versions v ON h.contract=v.contract "
            "AND h.version=v.version WHERE h.contract=?",
            (key,),
        ).fetchone()
        return sorted(
            set(
                proposal["scope"]
                + (json.loads(row[0])["scope"] if row else [])
                + (json.loads(current[0])["scope"] if current else [])
            )
        )

    def bootstrap_notices(self, db: sqlite3.Connection, task: dict[str, Any]) -> None:
        for key, decision in heads(db).items():
            if self.relevant(task, key, decision["scope"]):
                self.emit(
                    db,
                    task["task_id"],
                    "accepted_context",
                    {"contract": key, "version": decision["version"]},
                )
        for row in db.execute(
            "SELECT body FROM entities WHERE kind='proposal' AND json_extract(body,'$.status')='pending'"
        ):
            proposal = json.loads(row[0])
            key = f"{proposal['contract']['boundary']}::{proposal['contract']['key']}"
            if proposal["status"] == "pending" and self.relevant(
                task, key, self.proposal_scope(db, proposal)
            ):
                self.emit(
                    db,
                    task["task_id"],
                    "pending_impact",
                    {"proposal_id": proposal["proposal_id"], "contract": key},
                )

    def register(self, request: TaskRequest) -> dict[str, Any]:
        root = Path(request.worktree).resolve()
        self.worktree(root)
        baseline: str | None = None
        if self.config.common_dir:
            from decisionguard.domain.errors import GuardError

            try:
                baseline = git(root, "rev-parse", "--verify", "HEAD")
            except GuardError:
                pass  # An unborn branch has no baseline commit; all source paths are changed.
        for path in request.paths:
            safe_path(root, path)
        if request.integration:
            require(
                self.config.common_dir is not None and root != Path(self.config.root).resolve(),
                "INVALID",
                "Integration requires a separate linked worktree",
            )

        def action(db: sqlite3.Connection) -> dict[str, Any]:
            existing = db.execute(
                "SELECT 1 FROM entities WHERE kind='task' AND id=?", (request.task_id,)
            ).fetchone()
            require(
                existing is None,
                "INVALID",
                "Task already exists; register a new task for new scope",
            )
            active = heads(db)
            total = db.execute(
                "SELECT COUNT(*) FROM entities WHERE kind='task' AND COALESCE(json_extract(body,'$.archived'),0)=0"
            ).fetchone()[0]
            actor_total = db.execute(
                "SELECT COUNT(*) FROM entities WHERE kind='task' AND COALESCE(json_extract(body,'$.archived'),0)=0 AND json_extract(body,'$.actor')=?",
                (request.actor,),
            ).fetchone()[0]
            require(
                total < self.config.limits.tasks_per_project
                and actor_total < self.config.limits.tasks_per_actor,
                "RESOURCE_LIMIT",
                "Task quota reached",
            )
            dependencies: dict[str, int] = {}
            for contract in request.contracts:
                require(contract.identity in active, "NOT_FOUND", "Contract is not accepted")
                dependencies[contract.identity] = active[contract.identity]["version"]
            task = {
                **request.model_dump(exclude={"idempotency_key", "contracts"}),
                "worktree": str(root),
                "baseline_commit": baseline,
                "dependencies": dependencies,
                "evidence_generation": 0,
                "run_sequence": 0,
                "latest_run_id": None,
                "scope_revision": 0,
                "scope_approved": self.session_actor is None,
            }
            put(db, "task", request.task_id, task)
            db.execute("INSERT INTO cursors(task) VALUES(?)", (request.task_id,))
            self.bootstrap_notices(db, task)
            return {"task": task}

        return self.mutate("register_task", request, action)

    def assume(self, request: AssumeRequest) -> dict[str, Any]:
        def action(db: sqlite3.Connection) -> dict[str, Any]:
            task = self.task(db, request.task_id, request.actor)
            key = request.contract.identity
            active = heads(db)
            require(
                key in active and request.observed_version == active[key]["version"],
                "VERSION_CONFLICT",
                "Assumption must observe current version",
            )
            for path in request.evidence:
                safe_path(Path(task["worktree"]), path)
            body = request.model_dump(exclude={"idempotency_key"})
            put(db, "assumption", f"{request.task_id}|{key}", body)
            task["dependencies"][key] = request.observed_version
            put(db, "task", request.task_id, task)
            self.invalidate(db, request.task_id)
            self.bootstrap_notices(db, task)
            return {"assumption": body}

        return self.mutate("declare_assumption", request, action)

    def propose(
        self, request: ProposeRequest, *, _db: sqlite3.Connection | None = None
    ) -> dict[str, Any]:
        def action(db: sqlite3.Connection) -> dict[str, Any]:
            task = self.task(db, request.task_id, request.actor)
            from decisionguard.git.context import scoped_path

            require(
                task["scope_approved"]
                and all(
                    any(scoped_path(path, approved) for approved in task["paths"])
                    for path in request.scope
                ),
                "FORBIDDEN",
                "Proposal requires coordinator-approved task scope",
            )
            pending = [p for p in all_entities(db, "proposal") if p["status"] == "pending"]
            require(
                len(pending) < self.config.limits.pending_per_project
                and sum(p["actor"] == request.actor for p in pending)
                < self.config.limits.pending_per_actor,
                "RESOURCE_LIMIT",
                "Pending proposal quota reached",
            )
            for path in request.scope + request.evidence:
                safe_path(Path(task["worktree"]), path)
            active = heads(db)
            key = request.contract.identity
            actual = active.get(key, {}).get("version", 0)
            require(actual == request.expected_version, "VERSION_CONFLICT", "Predecessor changed")
            proposal_id = str(uuid.uuid4())
            body = {
                **request.model_dump(exclude={"idempotency_key"}),
                "proposal_id": proposal_id,
                "status": "pending",
                "timestamp": now(),
            }
            put(db, "proposal", proposal_id, body)
            affected = self.affected(db, key, self.proposal_scope(db, body))
            for task_id in affected:
                self.emit(
                    db, task_id, "pending_impact", {"proposal_id": proposal_id, "contract": key}
                )
            return {"proposal": body, "affected_tasks": affected}

        return action(_db) if _db is not None else self.mutate("propose_decision", request, action)

    def affected(
        self, db: sqlite3.Connection, key: str, scope: list[str] | None = None
    ) -> list[str]:
        tasks = [
            json.loads(row[0])
            for row in db.execute(
                "SELECT body FROM entities WHERE kind='task' AND COALESCE(json_extract(body,'$.archived'),0)=0"
            )
        ]
        return [task["task_id"] for task in tasks if self.relevant(task, key, scope or [])]

    def invalidate(self, db: sqlite3.Connection, task_id: str) -> None:
        task = get(db, "task", task_id)
        task["evidence_generation"] += 1
        put(db, "task", task_id, task)
        if task["latest_run_id"]:
            run = get(db, "run", task["latest_run_id"])
            run["valid"] = False
            put(db, "run", run["run_id"], run)

    def approve_scope(self, request: ScopeApproval) -> dict[str, Any]:
        self.authorize(request.actor, coordinator=True)

        def action(db: sqlite3.Connection) -> dict[str, Any]:
            task = self.task(db, request.task_id)
            require(
                task["scope_revision"] == request.expected_scope_revision,
                "VERSION_CONFLICT",
                "Task scope changed",
            )
            for path in request.paths:
                safe_path(Path(task["worktree"]), path)
            task.update(
                paths=request.paths, scope_approved=True, scope_revision=task["scope_revision"] + 1
            )
            put(db, "task", request.task_id, task)
            self.invalidate(db, request.task_id)
            self.bootstrap_notices(db, task)
            self.emit(
                db,
                request.task_id,
                "scope_approved",
                {
                    "paths": request.paths,
                    "reviewer": request.actor,
                    "scope_revision": task["scope_revision"],
                },
            )
            return {"task": get(db, "task", request.task_id)}

        return self.mutate("approve_task_scope", request, action)

    def review(self, request: ReviewRequest) -> dict[str, Any]:
        self.authorize(request.actor, coordinator=True)

        def action(db: sqlite3.Connection) -> dict[str, Any]:
            proposal = get(db, "proposal", request.proposal_id)
            require(proposal["actor"] != request.actor, "FORBIDDEN", "Self-review is forbidden")
            require(
                proposal["status"] == "pending", "VERSION_CONFLICT", "Proposal already reviewed"
            )
            key = f"{proposal['contract']['boundary']}::{proposal['contract']['key']}"
            active = heads(db)
            version = active.get(key, {}).get("version", 0)
            require(
                request.expected_version == proposal["expected_version"]
                and (not request.accept or request.expected_version == version),
                "VERSION_CONFLICT",
                "Expected predecessor changed",
            )
            proposal["status"] = "accepted" if request.accept else "rejected"
            proposal["review"] = request.model_dump(exclude={"idempotency_key"})
            put(db, "proposal", request.proposal_id, proposal)
            affected = self.affected(db, key, self.proposal_scope(db, proposal))
            if request.accept:
                decision = {
                    "contract": proposal["contract"],
                    "version": version + 1,
                    "value": proposal["value"],
                    "scope": proposal["scope"],
                    "owner": proposal["actor"],
                    "rationale": proposal["rationale"],
                    "predecessor": version or None,
                    "evidence": proposal["evidence"],
                    "timestamp": now(),
                }
                db.execute(
                    "INSERT INTO versions VALUES(?,?,?)", (key, version + 1, dumps(decision))
                )
                db.execute(
                    "INSERT INTO heads VALUES(?,?) ON CONFLICT(contract) "
                    "DO UPDATE SET version=excluded.version",
                    (key, version + 1),
                )
                db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
                for task_id in affected:
                    self.invalidate(db, task_id)
            for task_id in affected:
                self.emit(
                    db,
                    task_id,
                    proposal["status"],
                    {
                        "proposal_id": request.proposal_id,
                        "contract": key,
                        "version": version + 1 if request.accept else version,
                    },
                )
            put(
                db,
                "resolution",
                request.proposal_id,
                {
                    "proposal_id": request.proposal_id,
                    "status": proposal["status"],
                    "actor": request.actor,
                    "rationale": request.rationale,
                    "timestamp": now(),
                },
            )
            return {"proposal": proposal, "revision": revision(db), "affected_tasks": affected}

        return self.mutate("review_proposal", request, action)

    def refresh(self, request: TaskMutation) -> dict[str, Any]:
        def action(db: sqlite3.Connection) -> dict[str, Any]:
            task = self.task(db, request.task_id, request.actor)
            active = heads(db)
            for key in task["dependencies"]:
                task["dependencies"][key] = active[key]["version"]
            put(db, "task", request.task_id, task)
            for assumption in all_entities(db, "assumption"):
                if assumption["task_id"] == request.task_id:
                    key = f"{assumption['contract']['boundary']}::{assumption['contract']['key']}"
                    assumption["observed_version"] = active[key]["version"]
                    put(db, "assumption", f"{request.task_id}|{key}", assumption)
            self.invalidate(db, request.task_id)
            return {"task": task}

        return self.mutate("refresh_dependencies", request, action)

    def poll(self, task_id: str, actor: str, after: int = 0, limit: int = 100) -> dict[str, Any]:
        require(after >= 0 and 1 <= limit <= 100, "INVALID", "Invalid pagination")
        with self.store.transaction() as db:
            self.task(db, task_id, actor)
            delivered = db.execute(
                "SELECT delivered FROM cursors WHERE task=?", (task_id,)
            ).fetchone()[0]
            require(after <= delivered, "INVALID", "Cursor cannot skip undelivered events")
            events = [
                {"event_id": row[0], **json.loads(row[1])}
                for row in db.execute(
                    "SELECT id,body FROM events WHERE task=? AND id>? ORDER BY id LIMIT ?",
                    (task_id, after, limit),
                )
            ]
            if events:
                db.execute(
                    "UPDATE cursors SET delivered=MAX(delivered,?) WHERE task=?",
                    (events[-1]["event_id"], task_id),
                )
            cursor = dict(db.execute("SELECT * FROM cursors WHERE task=?", (task_id,)).fetchone())
            return envelope(events=events, cursor=cursor)

    def ack(self, request: AckRequest) -> dict[str, Any]:
        def action(db: sqlite3.Connection) -> dict[str, Any]:
            self.task(db, request.task_id, request.actor)
            cursor = db.execute(
                "SELECT delivered FROM cursors WHERE task=?", (request.task_id,)
            ).fetchone()
            event = db.execute("SELECT task FROM events WHERE id=?", (request.event_id,)).fetchone()
            require(
                event is not None and event[0] == request.task_id and cursor[0] >= request.event_id,
                "INVALID",
                "Event has not been delivered to this task",
            )
            db.execute(
                "UPDATE cursors SET ack=MAX(ack,?) WHERE task=?",
                (request.event_id, request.task_id),
            )
            return {"acknowledged": request.event_id, "validation_created": False}

        return self.mutate("acknowledge_event", request, action)

    def mapping(self, request: MappingRequest) -> dict[str, Any]:
        self.authorize(request.actor, coordinator=True)

        def action(db: sqlite3.Connection) -> dict[str, Any]:
            active = heads(db)
            require(
                request.source.identity in active and request.target.identity in active,
                "NOT_FOUND",
                "Both mapping boundaries must exist",
            )
            for path in request.evidence:
                safe_path(Path(self.config.root), path)
            body = request.model_dump(exclude={"idempotency_key"})
            body["mapping_id"] = str(uuid.uuid4())
            put(db, "mapping", body["mapping_id"], body)
            db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            for task in all_entities(db, "task"):
                if {request.source.identity, request.target.identity} & task["dependencies"].keys():
                    self.invalidate(db, task["task_id"])
                    self.emit(
                        db, task["task_id"], "mapping_reviewed", {"mapping_id": body["mapping_id"]}
                    )
            return {"mapping": body}

        return self.mutate("review_mapping", request, action)

    def context(self, task_id: str | None = None) -> dict[str, Any]:
        require(self._release.alive, "INVALID", "Service session is closed")
        with self.store.connect() as db:
            db.execute("BEGIN")
            task = self.task(db, task_id, self.session_actor) if task_id else None
            active = heads(db)
            if task:
                active = {k: v for k, v in active.items() if self.relevant(task, k, v["scope"])}
            return envelope(
                project=self.config.project,
                revision=revision(db),
                decisions=active,
                task=task,
                mappings=all_entities(db, "mapping"),
            )

    def findings(self, db: sqlite3.Connection, task_ids: list[str]) -> list[dict[str, Any]]:
        active = heads(db)
        findings: list[dict[str, Any]] = []
        mappings = all_entities(db, "mapping")
        marks = ",".join("?" for _ in task_ids) or "NULL"
        assumptions = [
            json.loads(row[0])
            for row in db.execute(
                f"SELECT body FROM entities WHERE kind='assumption' AND json_extract(body,'$.task_id') IN ({marks})",
                task_ids,
            )
        ]
        pending = [
            json.loads(row[0])
            for row in db.execute(
                "SELECT body FROM entities WHERE kind='proposal' AND json_extract(body,'$.status')='pending'"
            )
        ]

        def add(
            kind: str,
            task_id: str,
            key: str,
            expected: Any,
            actual: Any,
            evidence: Any,
            action: str,
        ) -> None:
            findings.append(
                {
                    "kind": kind,
                    "task_id": task_id,
                    "contract": key,
                    "expected": expected,
                    "active": actual,
                    "rule": kind,
                    "evidence": evidence,
                    "next_action": action,
                }
            )

        for task_id in task_ids:
            task = self.task(db, task_id)
            for key, observed in task["dependencies"].items():
                decision = active[key]
                if observed != decision["version"]:
                    add(
                        "stale_dependencies",
                        task_id,
                        key,
                        observed,
                        decision["version"],
                        [],
                        "Retrieve context, revisit code, refresh dependencies, then validate",
                    )
                declared = [
                    a
                    for a in assumptions
                    if a["task_id"] == task_id
                    and f"{a['contract']['boundary']}::{a['contract']['key']}" == key
                ]
                if not declared:
                    add(
                        "incomplete_coverage",
                        task_id,
                        key,
                        None,
                        decision["value"],
                        [],
                        "Declare the implementation assumption",
                    )
                for assumption in declared:
                    expected = Value.model_validate(assumption["expected"])
                    actual = Value.model_validate(decision["value"])
                    compatible = any(
                        m["source"] == decision["contract"] == m["target"]
                        and (
                            (
                                m["source_value"] == expected.model_dump()
                                and m["target_value"] == actual.model_dump()
                            )
                            or (
                                m["target_value"] == expected.model_dump()
                                and m["source_value"] == actual.model_dump()
                            )
                        )
                        for m in mappings
                    )
                    result = "equal" if compatible else compare(expected, actual)
                    details: list[dict[str, str]] = []
                    if (
                        not compatible
                        and expected.kind == actual.kind == "schema"
                        and not (expected.deleted or actual.deleted)
                    ):
                        from decisionguard.domain.schemas import compare_artifacts

                        documents = [
                            db.execute(
                                "SELECT body FROM artifacts WHERE digest=?",
                                (v.value.removeprefix("sha256:"),),
                            ).fetchone()
                            for v in (expected, actual)
                        ]
                        if all(documents):
                            result, details = compare_artifacts(
                                json.loads(documents[0][0]), json.loads(documents[1][0])
                            )
                    if result != "equal":
                        add(
                            "confirmed_conflict"
                            if result == "incompatible"
                            else "unknown_compatibility",
                            task_id,
                            key,
                            expected.model_dump(),
                            actual.model_dump(),
                            assumption["evidence"],
                            "Reconcile declarations or review compatibility",
                        )
                        if details:
                            findings[-1]["details"] = details
            for proposal in pending:
                key = f"{proposal['contract']['boundary']}::{proposal['contract']['key']}"
                if proposal["status"] == "pending" and self.relevant(
                    task, key, self.proposal_scope(db, proposal)
                ):
                    add(
                        "pending_impact",
                        task_id,
                        key,
                        proposal["value"],
                        active.get(key, {}).get("value"),
                        [proposal["proposal_id"]],
                        "Coordinator must accept or reject the proposal",
                    )
        return findings

    @staticmethod
    def overlap(a: str, b: str) -> bool:
        from decisionguard.git.context import scoped_path

        return scoped_path(a, b) or scoped_path(b, a)

    def conflicts(self, task_ids: list[str] | None = None) -> dict[str, Any]:
        with self.store.connect() as db:
            db.execute("BEGIN")
            selected = (
                task_ids
                if task_ids is not None
                else [
                    task["task_id"]
                    for task in all_entities(db, "task")
                    if not task.get("archived", False)
                ]
            )
            return envelope(findings=self.findings(db, selected), revision=revision(db))

    def impact(self, task_ids: list[str] | None = None) -> dict[str, Any]:
        """Explain declared impacts and evidence metadata without running tests or writing receipts."""
        config_digest = digest(load_config(self.directory).model_dump())
        with self.store.connect() as db:
            db.execute("BEGIN")
            selected = (
                task_ids
                if task_ids is not None
                else [
                    row[0]
                    for row in db.execute(
                        "SELECT id FROM entities WHERE kind='task' AND COALESCE(json_extract(body,'$.archived'),0)=0"
                    )
                ]
            )
            require(
                len(selected) <= 1000 and len(set(selected)) == len(selected),
                "INVALID",
                "Select distinct tasks",
            )
            findings = self.findings(db, selected)
            tasks = {}
            for identity in selected:
                task = self.task(db, identity)
                run = get(db, "run", task["latest_run_id"]) if task["latest_run_id"] else None
                stale = (
                    run is None
                    or not run["valid"]
                    or not run["passed"]
                    or run["status"] != "finished"
                    or run["revision"] != revision(db)
                    or run["config_digest"] != config_digest
                    or run["evidence_generation"] != task["evidence_generation"]
                )
                tasks[identity] = {
                    "latest_run_id": task["latest_run_id"],
                    "latest_run_status": run["status"] if run else "missing",
                    "validation_required": stale,
                    "source_freshness": "requires_gate_check",
                    "next_action": "Revisit code and run configured local validation"
                    if stale
                    else "Check the gate to recompute source freshness",
                }
            return envelope(
                findings=findings,
                tasks=tasks,
                revision=revision(db),
                source_freshness_checked=False,
                receipt_created=False,
            )
