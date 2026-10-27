"""Local OpenAPI previews and atomic, explicitly reviewed contract publication."""

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from decisionguard.application.services import Service, digest, envelope
from decisionguard.domain.contracts import ContractPublish, ContractScan
from decisionguard.domain.errors import require
from decisionguard.domain.models import ProposeRequest, Value
from decisionguard.domain.schemas import compare_artifacts, issues, normalized
from decisionguard.git.context import safe_path, scoped_path
from decisionguard.storage.sqlite import heads


def resolve(
    document: dict[str, Any],
    value: Any,
    seen: tuple[str, ...] = (),
    depth: int = 0,
    budget: list[int] | None = None,
) -> Any:
    if budget is None:
        budget = [50000, 131072]
    budget[0] -= 1
    require(budget[0] >= 0, "RESOURCE_LIMIT", "Resolved OpenAPI node budget exceeded")
    require(depth <= 64, "RESOURCE_LIMIT", "OpenAPI depth exceeds 64")
    if isinstance(value, str):
        budget[1] -= len(value.encode("utf-8"))
    elif isinstance(value, dict):
        budget[1] -= sum(len(k.encode("utf-8")) for k in value)
    else:
        budget[1] -= 8
    require(budget[1] >= 0, "RESOURCE_LIMIT", "Resolved OpenAPI text exceeds 128 KiB")
    if isinstance(value, list):
        return [resolve(document, v, seen, depth + 1, budget) for v in value]
    if not isinstance(value, dict):
        return value
    if "$ref" in value:
        ref = value["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen or len(value) != 1:
            return {"unsupportedReference": ref}
        target: Any = document
        try:
            for part in ref[2:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError):
            return {"unsupportedReference": ref}
        return resolve(document, target, (*seen, ref), depth + 1, budget)
    return {key: resolve(document, v, seen, depth + 1, budget) for key, v in value.items()}


def scoped_file(service: Service, task_id: str, relative: str) -> tuple[Path, dict[str, Any]]:
    with service.store.connect() as db:
        task = service.task(db, task_id, service.session_actor)
    require(task["scope_approved"], "FORBIDDEN", "Task scope awaits approval")
    require(
        any(scoped_path(relative, p) for p in task["paths"]),
        "FORBIDDEN",
        "File outside approved scope",
    )
    path = safe_path(Path(task["worktree"]), relative)
    require(
        ".git" not in {part.lower() for part in path.relative_to(Path(task["worktree"])).parts},
        "FORBIDDEN",
        "Git metadata cannot be scanned",
    )
    require(
        not path.is_relative_to(service.directory), "FORBIDDEN", "State files cannot be scanned"
    )
    return path, task


def scan(service: Service, request: ContractScan) -> dict[str, Any]:
    path, task = scoped_file(service, request.task_id, request.spec)
    require(
        path.is_file() and path.stat().st_size <= 10 * 1024 * 1024,
        "RESOURCE_LIMIT",
        "OpenAPI input missing or exceeds 10 MiB",
    )
    with path.open("rb") as stream:
        raw = stream.read(10 * 1024 * 1024 + 1)
    require(len(raw) <= 10 * 1024 * 1024, "RESOURCE_LIMIT", "OpenAPI input exceeds 10 MiB")
    try:
        document = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ValueError("Invalid or excessively nested OpenAPI JSON") from exc
    require(
        isinstance(document, dict)
        and re.fullmatch(r"3\.1\.\d+", str(document.get("openapi", ""))) is not None,
        "INVALID",
        "Only OpenAPI 3.1.x JSON is supported",
    )
    with service.store.connect() as db:
        active = heads(db)
        artifacts = {}
        for decision in active.values():
            fingerprint = decision["value"]["value"].removeprefix("sha256:")
            row = db.execute("SELECT body FROM artifacts WHERE digest=?", (fingerprint,)).fetchone()
            if row:
                artifacts[fingerprint] = json.loads(row[0])
    proposals: list[dict[str, Any]] = []
    resolution_budget = [50000, 131072]
    for binding in request.bindings:
        for relative in binding.scope:
            safe_path(Path(task["worktree"]), relative)
            require(
                any(scoped_path(relative, p) for p in task["paths"]),
                "FORBIDDEN",
                "Binding exceeds approved scope",
            )
        paths = document.get("paths", {})
        require(isinstance(paths, dict), "INVALID", "OpenAPI paths must be an object")
        path_item = resolve(document, paths.get(binding.path, {}), budget=resolution_budget)
        require(isinstance(path_item, dict), "INVALID", "OpenAPI path item must be an object")
        operation = path_item.get(binding.method)
        require(
            operation is None or isinstance(operation, dict),
            "INVALID",
            "OpenAPI operation must be an object",
        )
        missing = operation is None and "unsupportedReference" not in path_item
        operation = operation if isinstance(operation, dict) else {}
        unsupported: list[dict[str, str]] = []
        if "unsupportedReference" in path_item:
            unsupported.append({"pointer": "/paths", "reason": "Unresolved path reference"})
        if any("servers" in x for x in (document, path_item, operation)):
            unsupported.append(
                {"pointer": "/servers", "reason": "Server URL compatibility is not covered"}
            )
        required = False
        if binding.direction == "security":
            security = operation.get("security", document.get("security", []))
            components = document.get("components", {})
            require(isinstance(components, dict), "INVALID", "Components must be an object")
            schemes = components.get("securitySchemes", {})
            require(isinstance(schemes, dict), "INVALID", "Security schemes must be an object")
            require(
                isinstance(security, list) and all(isinstance(x, dict) for x in security),
                "INVALID",
                "Invalid security requirements",
            )
            used = {k for item in security for k in item}
            require(
                all(
                    isinstance(v, list) and all(isinstance(scope, str) for scope in v)
                    for item in security
                    for v in item.values()
                ),
                "INVALID",
                "Invalid security scopes",
            )
            if any(k not in schemes for k in used):
                unsupported.append({"pointer": "/security", "reason": "Unresolved security scheme"})
            resolved_schemes = {
                k: resolve(document, schemes.get(k), budget=resolution_budget) for k in sorted(used)
            }
            if any(
                not isinstance(v, dict) or "unsupportedReference" in v
                for v in resolved_schemes.values()
            ):
                unsupported.append(
                    {"pointer": "/security", "reason": "Unresolved security scheme reference"}
                )
            schema = {
                "requirements": sorted(
                    [{k: sorted(v) for k, v in item.items()} for item in security], key=normalized
                ),
                "schemes": resolved_schemes,
            }
        else:
            responses = operation.get("responses", {})
            require(isinstance(responses, dict), "INVALID", "Responses must be an object")
            if (
                binding.direction == "response"
                and binding.status not in responses
                and "unsupportedReference" not in path_item
            ):
                missing = missing or "unsupportedReference" not in responses
            container = (
                operation.get("requestBody", {})
                if binding.direction == "request"
                else responses.get(binding.status, {})
            )
            require(isinstance(container, dict), "INVALID", "Body or response must be an object")
            if "unsupportedReference" in container:
                unsupported.append({"pointer": "/content", "reason": "Unresolved body reference"})
            required = container.get("required", False) if binding.direction == "request" else False
            content = container.get("content", {})
            require(
                isinstance(content, dict) and isinstance(content.get("application/json", {}), dict),
                "INVALID",
                "Content and media types must be objects",
            )
            schema = content.get("application/json", {}).get("schema", {})
            if set(content) - {"application/json"}:
                unsupported.append(
                    {"pointer": "/content", "reason": "Only application/json is covered"}
                )
            if binding.direction == "request" and (
                operation.get("parameters") or path_item.get("parameters")
            ):
                unsupported.append(
                    {"pointer": "/parameters", "reason": "Non-body parameters are not covered"}
                )
            unsupported.extend(issues(schema))
            if container.get("headers"):
                unsupported.append(
                    {
                        "pointer": "/headers",
                        "reason": "Response header compatibility is not covered",
                    }
                )
        artifact = {
            "direction": binding.direction,
            "method": binding.method,
            "path": binding.path,
            "status": binding.status,
            "schema": schema,
            "required": required,
            "missing": missing,
            "unsupported": unsupported,
            "producers": binding.producers,
            "consumers": binding.consumers,
        }
        fingerprint = digest(artifact)
        value = Value(kind="schema", value="sha256:" + fingerprint, deleted=missing)
        previous = active.get(binding.contract.identity)
        outcome, reasons = "unknown", unsupported
        if previous:
            old = artifacts.get(previous["value"]["value"].removeprefix("sha256:"))
            if old:
                outcome, reasons = compare_artifacts(old, artifact)
        proposals.append(
            {
                "contract": binding.contract.model_dump(),
                "value": value.model_dump(),
                "scope": binding.scope,
                "artifact": artifact,
                "artifact_digest": fingerprint,
                "comparison": outcome,
                "details": reasons,
            }
        )
        for unit in binding.units:
            require(
                unit.pointer.startswith("/"),
                "INVALID",
                "Field pointer must be a schema JSON pointer",
            )
            node: Any = schema
            try:
                for token in unit.pointer[1:].split("/"):
                    node = node[token.replace("~1", "/").replace("~0", "~")]
            except (KeyError, TypeError):
                require(
                    False, "INVALID", "Field template pointer does not exist in selected schema"
                )
            require(
                unit.value.kind
                in {"money_unit", "time_unit", "auth", "idempotency", "error_format"},
                "INVALID",
                "Unsupported field template kind",
            )
            proposals.append(
                {
                    "contract": unit.contract.model_dump(),
                    "value": unit.value.model_dump(),
                    "scope": binding.scope,
                    "pointer": unit.pointer,
                }
            )
    identities = [f"{p['contract']['boundary']}::{p['contract']['key']}" for p in proposals]
    require(len(set(identities)) == len(identities), "INVALID", "Duplicate contract binding")
    preview = {
        "request": request.model_dump(),
        "source_digest": digest(raw.hex()),
        "proposals": proposals,
    }
    require(
        len(normalized(preview).encode("utf-8")) <= 10 * 1024 * 1024,
        "RESOURCE_LIMIT",
        "Selected contract preview exceeds 10 MiB",
    )
    return envelope(**preview, preview_digest=digest(preview), acceptance_required=True)


def publish(service: Service, request: ContractPublish) -> dict[str, Any]:
    service.authorize(request.actor)
    with service.store.connect() as db:
        service.task(db, request.scan.task_id, request.actor)
        previous = db.execute(
            "SELECT fingerprint,result FROM retries WHERE actor=? AND key=?",
            (request.actor, request.idempotency_key),
        ).fetchone()
        if previous:
            require(
                previous[0]
                == digest({"operation": "publish_contracts", "request": request.model_dump()}),
                "IDEMPOTENCY_CONFLICT",
                "Retry payload differs",
            )
            return dict(json.loads(previous[1]))
    preview = scan(service, request.scan)
    require(
        preview["preview_digest"] == request.preview_digest,
        "SOURCE_CHANGED",
        "Contract preview changed; scan again",
    )

    def action(db: sqlite3.Connection) -> dict[str, Any]:
        results = []
        for item in preview["proposals"]:
            key = f"{item['contract']['boundary']}::{item['contract']['key']}"
            require(
                key in request.expected_versions,
                "INVALID",
                "Provide every expected contract version",
            )
            if "artifact" in item:
                db.execute(
                    "INSERT OR IGNORE INTO artifacts VALUES(?,?)",
                    (item["artifact_digest"], normalized(item["artifact"])),
                )
            proposal = ProposeRequest.model_validate(
                {
                    "actor": request.actor,
                    "task_id": request.scan.task_id,
                    "idempotency_key": request.idempotency_key,
                    "contract": item["contract"],
                    "value": item["value"],
                    "expected_version": request.expected_versions[key],
                    "scope": item["scope"],
                    "rationale": request.rationale,
                    "evidence": [request.scan.spec],
                }
            )
            results.append(service.propose(proposal, _db=db))
        return {"proposals": results, "acceptance_required": True}

    return service.mutate("publish_contracts", request, action)
