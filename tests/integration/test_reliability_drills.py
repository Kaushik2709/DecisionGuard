import json
import os
import sqlite3
import subprocess
import sys

import pytest

from decisionguard.domain.errors import GuardError
from decisionguard.reports.reliability import filesystem_full_drill, recovery_drill, soak


def test_killed_writer_lost_response_capacity_and_restore(tmp_path):
    result = recovery_drill(tmp_path / "recovery")
    assert result["killed_before_commit_rolled_back"]
    assert result["killed_after_commit_retry_unchanged"]
    assert result["restored_gate_blocked"] and result["restored_history_preserved"]
    assert result["capacity_limit"]["sqlite_full_observed"]
    assert not result["capacity_limit"]["physical_disk_full"]


def test_real_worktree_soak_reports_duration_history_and_limits(tmp_path):
    result = soak(tmp_path / "soak", seconds=1.0, workers=2, history=50)
    assert result["passed"] and result["workers"] == 2
    assert result["seeded_history_events"] == 50
    assert result["latencies"]["gate"]["samples"] >= 2
    assert all(result["quiescent_gates"].values())
    assert not result["full_8_hour_soak_completed"]
    assert not result["production_reliability_established"]
    assert result["latencies"]["validation"]["p95_ms"] >= 0
    assert all(o["python_tracemalloc_peak_bytes"] > 0 for o in result["worker_results"])
    assert result["process_rss_peak_bytes"] is None
    with pytest.raises(GuardError, match="new disposable"):
        soak(tmp_path / "soak", seconds=1)


@pytest.mark.parametrize(
    "seconds,workers,history", [(float("nan"), 2, 0), (-1, 2, 0), (1, 5, 0), (1, 2, 100001)]
)
def test_invalid_load_does_not_create_a_fixture(tmp_path, seconds, workers, history):
    destination = tmp_path / "absent"
    with pytest.raises(GuardError):
        soak(destination, seconds=seconds, workers=workers, history=history)
    assert not destination.exists()


@pytest.mark.skipif(
    os.environ.get("DECISIONGUARD_BOUNDED_FS_TEST") != "1",
    reason="Requires a separately mounted disposable <=16 MiB filesystem",
)
def test_actual_bounded_filesystem_full_and_recovery(tmp_path):
    result = filesystem_full_drill(tmp_path / "full")
    assert result["filesystem_full_observed"]
    assert result["history_preserved"] and result["subsequent_mutation_passed"]
    assert result["retry_absent"] and result["integrity_ok"]


def test_corrupt_state_cli_fails_without_reinitializing(project, tmp_path):
    service, root = project
    service.close()
    state = service.directory / "state.db"
    # Controlled corruption of this disposable fixture only, with closed connections.
    corrupted = b"This is deliberately not a SQLite database" * 256
    state.write_bytes(corrupted)
    result = subprocess.run(
        [sys.executable, "-m", "decisionguard.adapters.cli", "--root", str(root), "doctor"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["error"]["code"] == "INVALID"
    assert state.read_bytes() == corrupted
    with pytest.raises(sqlite3.DatabaseError):
        with sqlite3.connect(state) as db:
            db.execute("PRAGMA integrity_check")
