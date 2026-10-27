import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(
    shutil.which("node") is None, reason="Optional Node 24 fixture runtime is not installed"
)
def test_real_typescript_python_http_mismatch_and_repair(tmp_path):
    source = Path(__file__).resolve().parents[2] / "examples" / "fullstack-checkout"
    for filename in ("api.py", "client.ts", "verify.py"):
        shutil.copyfile(source / filename, tmp_path / filename)

    def run():
        return subprocess.run(
            [sys.executable, str(tmp_path / "verify.py")],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    baseline = run()
    assert baseline.returncode == 0, baseline.stderr
    frontend = tmp_path / "client.ts"
    frontend.write_text(frontend.read_text().replace("= 499;", "= 49900;"))
    mismatch = run()
    assert mismatch.returncode != 0 and "4990000" in mismatch.stderr
    backend = tmp_path / "api.py"
    backend.write_text(
        backend.read_text().replace("Decimal(str(amount)) * 100", "Decimal(str(amount))")
    )
    assert run().returncode == 0
