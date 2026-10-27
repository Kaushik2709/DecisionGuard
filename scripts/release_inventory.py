"""Write an honest installed-environment dependency inventory, without credentials or URLs."""

import argparse
import importlib.metadata
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
arguments = parser.parse_args()
rows = []
for distribution in importlib.metadata.distributions():
    metadata = distribution.metadata
    rows.append(
        {
            "name": metadata["Name"],
            "version": distribution.version,
            "license_expression": metadata.get("License-Expression", "unknown"),
            "license_classifiers": [
                c for c in metadata.get_all("Classifier", []) if c.startswith("License ::")
            ],
        }
    )
result = {
    "schema_version": 1,
    "scope": "installed_environment_including_development_tools",
    "dependency_license_review_complete": False,
    "components": sorted(rows, key=lambda row: row["name"].lower()),
}
with arguments.output.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
print(json.dumps({"output": str(arguments.output), "component_count": len(rows)}))
