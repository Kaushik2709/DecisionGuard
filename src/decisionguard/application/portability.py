import json
from pathlib import Path
from typing import Any

from decisionguard.application.services import Service, digest
from decisionguard.domain.errors import require
from decisionguard.domain.models import Contract, Mutation, PortableMetadata, Value
from decisionguard.git.context import safe_path
from decisionguard.storage.sqlite import all_entities, dumps, heads, put, revision


def export_metadata(service: Service) -> dict[str, Any]:
    with service.store.connect() as db:
        db.execute("BEGIN")
        versions = [
            json.loads(row[0])
            for row in db.execute("SELECT body FROM versions ORDER BY contract,version")
        ]
        required = {
            v["value"]["value"].removeprefix("sha256:")
            for v in versions
            if v["value"]["kind"] == "schema"
        }
        artifacts = {}
        for key in required:
            row = db.execute("SELECT body FROM artifacts WHERE digest=?", (key,)).fetchone()
            if row:
                artifacts[key] = json.loads(row[0])
        return dict(
            schema_version=2,
            origin_project=service.config.project,
            origin_revision=revision(db),
            versions=versions,
            heads={k: v["version"] for k, v in heads(db).items()},
            mappings=all_entities(db, "mapping"),
            artifacts=artifacts,
        )


def import_metadata(
    service: Service, request: Mutation, metadata: dict[str, Any]
) -> dict[str, Any]:
    service.authorize(request.actor, coordinator=True)
    require(metadata.get("schema_version") in (1, 2), "INVALID", "Unsupported export schema")
    metadata = PortableMetadata.model_validate(metadata).model_dump()
    require(
        metadata["schema_version"] == 2 or not metadata["artifacts"],
        "INVALID",
        "Artifacts require export schema 2",
    )
    for fingerprint, artifact in metadata["artifacts"].items():
        require(digest(artifact) == fingerprint, "INVALID", "Artifact digest mismatch")
        require(
            artifact.get("direction") in {"request", "response", "security"}
            and isinstance(artifact.get("schema"), dict)
            and isinstance(artifact.get("unsupported"), list),
            "INVALID",
            "Invalid contract artifact",
        )
    by_contract: dict[str, list[int]] = {}
    for decision in metadata["versions"]:
        identity = Contract.model_validate(decision["contract"]).identity
        version = decision["version"]
        require(
            decision["predecessor"] == (version - 1 or None), "INVALID", "Invalid predecessor chain"
        )
        by_contract.setdefault(identity, []).append(version)
    require(
        set(metadata["heads"]) == set(by_contract), "INVALID", "Export heads do not cover history"
    )
    for identity, versions in by_contract.items():
        require(
            sorted(versions) == list(range(1, len(versions) + 1))
            and metadata["heads"][identity] == max(versions),
            "INVALID",
            "Incomplete accepted history",
        )
    require(
        len({m["mapping_id"] for m in metadata["mappings"]}) == len(metadata["mappings"]),
        "INVALID",
        "Duplicate reviewed mappings",
    )
    for mapping in metadata["mappings"]:
        require(
            all(
                Contract.model_validate(mapping[side]).identity in metadata["heads"]
                for side in ["source", "target"]
            ),
            "INVALID",
            "Mapping references unknown contract",
        )

    def action(db: Any) -> dict[str, Any]:
        require(
            not heads(db) and not all_entities(db, "task"),
            "INVALID",
            "Import requires empty project",
        )
        root = Path(service.config.root)
        for fingerprint, artifact in metadata["artifacts"].items():
            db.execute("INSERT INTO artifacts VALUES(?,?)", (fingerprint, dumps(artifact)))
        for decision in metadata["versions"]:
            contract = Contract.model_validate(decision["contract"])
            Value.model_validate(decision["value"])
            require(
                isinstance(decision["version"], int) and decision["version"] > 0,
                "INVALID",
                "Invalid decision version",
            )
            for path in decision["scope"] + decision["evidence"]:
                safe_path(root, path)
            db.execute(
                "INSERT INTO versions VALUES(?,?,?)",
                (contract.identity, decision["version"], dumps(decision)),
            )
        for key, version in metadata["heads"].items():
            db.execute("INSERT INTO heads VALUES(?,?)", (key, version))
        for mapping in metadata["mappings"]:
            from decisionguard.domain.models import MappingRequest

            checked = MappingRequest.model_validate(
                {
                    **{k: v for k, v in mapping.items() if k != "mapping_id"},
                    "idempotency_key": "import",
                }
            )
            for path in checked.evidence:
                safe_path(root, path)
            put(db, "mapping", mapping["mapping_id"], mapping)
        db.execute("UPDATE meta SET value='1' WHERE key='revision'")
        put(
            db,
            "import",
            digest(metadata),
            {
                "origin_project": metadata["origin_project"],
                "digest": digest(metadata),
                "reviewer": request.actor,
            },
        )
        return {"imported": True, "fresh_validation_required": True}

    # Bind retry identity to the metadata payload as well as actor/key.
    class ImportRequest(Mutation):
        metadata_digest: str

    bound = ImportRequest(**request.model_dump(), metadata_digest=digest(metadata))
    return service.mutate("import_metadata", bound, action)
