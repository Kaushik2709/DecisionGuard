"""Inspect a built wheel and retain hashes; no extraction, upload or publication."""

import argparse
import hashlib
import json
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path


def inspect(wheel: Path) -> dict:
    required = {
        "decisionguard/py.typed",
        "decisionguard/resources/decisionguard-workflow/SKILL.md",
        "decisionguard/application/onboarding.py",
        "decisionguard/reports/reliability.py",
        "decisionguard/application/product_evaluation.py",
    }
    with zipfile.ZipFile(wheel) as archive:
        members = archive.infolist()
        if len(members) > 5000 or sum(m.file_size for m in members) > 10 * 1024 * 1024:
            raise ValueError("Unexpectedly large wheel")
        names = {m.filename for m in members}
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if not required <= names or len(metadata_names) != 1:
            raise ValueError("Missing required packaged modules, skill or metadata")
        if any(
            set(Path(name).parts) & {".git", "node_modules", "__pycache__", ".env", "state.db"}
            for name in names
        ):
            raise ValueError("Unexpected local state in wheel")
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        if metadata["Name"] != "decisionguard" or metadata["License-Expression"] != "MIT":
            raise ValueError("Unexpected project or license metadata")
        license_name = metadata_names[0].removesuffix("METADATA") + "licenses/LICENSE"
        if archive.read(license_name) != Path("LICENSE").read_bytes():
            raise ValueError("Packaged license differs from repository license")
        files = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(names)}
    source = wheel.parent / f"decisionguard-{metadata['Version']}.tar.gz"
    with tarfile.open(source) as archive:
        members = archive.getmembers()
        if len(members) > 5000 or sum(m.size for m in members) > 20 * 1024 * 1024:
            raise ValueError("Unexpectedly large source archive")
        forbidden = {
            "node_modules",
            ".git",
            ".env",
            "state.db",
            "__pycache__",
            "artifacts",
            ".cache",
            ".cache-clean",
            ".venv",
        }
        if any(set(Path(m.name).parts) & forbidden or ".." in Path(m.name).parts for m in members):
            raise ValueError("Unexpected local dependencies or state in source archive")
    return {
        "schema_version": 1,
        "wheel": wheel.name,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "version": metadata["Version"],
        "source_archive_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_archive_checked": True,
        "packaging_checks_passed": True,
        "publication_performed": False,
        "stable_release_approved": False,
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.wheel)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "files"}))


if __name__ == "__main__":
    main()
