"""Fixed, local baseline commands. Installs nothing and never executes supplied manifests."""

import argparse
import importlib.metadata
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--tools-root", type=Path, default=Path(__file__).resolve().parent)
args = parser.parse_args()
root = Path(__file__).resolve().parent
tools = args.tools_root.resolve()
node = shutil.which("node")
codegen = tools / "node_modules/openapi-typescript/bin/cli.js"
compiler = tools / "node_modules/typescript/lib/tsc.js"
expected = json.loads((root / "package.json").read_text(encoding="utf-8"))["devDependencies"]
available = node is not None and codegen.is_file() and compiler.is_file()
if available:
    for package, version in expected.items():
        installed = json.loads(
            (tools / "node_modules" / package / "package.json").read_text(encoding="utf-8")
        )
        available = available and installed["version"] == version

commands = {
    "schema_validation": [[sys.executable, "-B", "schema_check.py"]],
    "codegen": [
        [node, str(codegen), "openapi.json", "--output", "schema.d.ts", "--check"],
        [node, str(compiler), "--project", "tsconfig.json", "--pretty", "false"],
    ]
    if available
    else [],
    "contract_tests": [[sys.executable, "-B", "contract_check.py"]],
    "integration_tests": [[sys.executable, "-B", "verify_http.py"]] if node else [],
}
rows = {}
for name, group in commands.items():
    started = time.perf_counter()
    outputs = []
    status = "passed" if group else "unsupported"
    for command in group:
        try:
            result = subprocess.run(
                command,
                cwd=root,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            outputs.append(
                {
                    "argv": command,
                    "exit_code": result.returncode,
                    "stdout": result.stdout[-16000:],
                    "stderr": result.stderr[-16000:],
                }
            )
            if result.returncode:
                status = "failed"
        except (OSError, subprocess.TimeoutExpired):
            status = "error"
    rows[name] = {
        "status": status,
        "elapsed_seconds": time.perf_counter() - started,
        "commands": outputs,
    }
report = {
    "schema_version": 1,
    "fixture_only": True,
    "checks": rows,
    "pinned_node_packages": expected,
    "jsonschema_version": importlib.metadata.version("jsonschema"),
    "passed": all(r["status"] == "passed" for r in rows.values()),
    "complete": all(r["status"] in {"passed", "failed"} for r in rows.values()),
    "effectiveness_claim_approved": False,
}
print(json.dumps(report))
raise SystemExit(0 if report["passed"] else 1 if report["complete"] else 2)
