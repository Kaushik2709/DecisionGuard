"""Test the built wheel from a separate cwd with locked dependencies and no PYTHONPATH."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="decisionguard-installed-wheel-") as staging:
        location = Path(staging)
        venv = location / "venv"
        environment["UV_PROJECT_ENVIRONMENT"] = str(venv)
        subprocess.run(
            [
                "uv",
                "sync",
                "--locked",
                "--group",
                "dev",
                "--no-install-project",
                "--python",
                sys.executable,
                "--offline",
            ],
            cwd=root,
            env=environment,
            check=True,
            timeout=180,
        )
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                "--offline",
                str(args.wheel.resolve()),
            ],
            env=environment,
            check=True,
            timeout=60,
        )
        cwd = location / "outside-checkout"
        cwd.mkdir()
        origin = subprocess.check_output(
            [str(python), "-c", "import decisionguard; print(decisionguard.__file__)"],
            cwd=cwd,
            env=environment,
            text=True,
            timeout=15,
        ).strip()
        if not Path(origin).resolve().is_relative_to(venv.resolve()):
            raise SystemExit("Wheel verification imported source outside the isolated environment")
        subprocess.run(
            [str(python), "-m", "decisionguard.adapters.cli", "runtime"],
            cwd=cwd,
            env=environment,
            check=True,
            timeout=15,
        )
        subprocess.run(
            [
                str(python),
                "-m",
                "pytest",
                str(root / "tests/transport"),
                str(root / "tests/integration/test_operations.py"),
                str(root / "tests/integration/test_worktrees_and_concurrency.py"),
                "-q",
                "--basetemp",
                str(output / "tmp"),
                "--junitxml",
                str(output / "installed-wheel.xml"),
            ],
            cwd=cwd,
            env=environment,
            check=True,
            timeout=300,
        )
        (output / "installed-wheel.json").write_text(
            json.dumps(
                {
                    "wheel": args.wheel.name,
                    "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                    "import_origin": origin,
                    "isolated_import_verified": True,
                    "transport_and_lifecycle_tests_passed": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
