import json
import subprocess
import sys
from pathlib import Path


def cli(cwd, *args):
    return subprocess.run(
        [sys.executable, "-m", "decisionguard.adapters.cli", *map(str, args)],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_product_study_cli_without_database_and_safe_errors(tmp_path):
    example = Path(__file__).resolve().parents[2] / "examples" / "product-study"
    plan = example / "plan.json"
    observations = example / "observations.json"
    initial_files = set(tmp_path.iterdir())
    result = cli(tmp_path, "evaluation", "schema")
    assert result.returncode == 0
    assert "StudyCase" in json.loads(result.stdout)["plan"]["$defs"]
    result = cli(tmp_path, "evaluation", "report", plan, observations)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["fixture_only"] and report["eligible_pairs"] == 0
    assert report["metrics"]["baseline"]["early_detections"]["rate"] is None
    assert set(tmp_path.iterdir()) == initial_files
    content = json.loads(observations.read_text(encoding="utf-8"))
    content["plan_sha256"] = "0" * 64
    malformed = tmp_path / "observations.json"
    malformed.write_text(json.dumps(content), encoding="utf-8")
    result = cli(tmp_path, "evaluation", "report", plan, malformed)
    assert result.returncode == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID"
    malformed.write_text('{"private-input":"do-not-print"}', encoding="utf-8")
    result = cli(tmp_path, "evaluation", "report", plan, malformed)
    assert result.returncode == 2 and "do-not-print" not in result.stdout + result.stderr
