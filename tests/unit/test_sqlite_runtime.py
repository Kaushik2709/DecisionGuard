import json
import sqlite3

import pytest
from typer.testing import CliRunner

from decisionguard.adapters.cli import app
from decisionguard.application.config import initialize
from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import RunnerConfig
from decisionguard.storage.runtime import runtime_status
from decisionguard.storage.sqlite import Store


@pytest.mark.parametrize(
    "version,patched",
    [
        ((3, 44, 5), False),
        ((3, 44, 6), True),
        ((3, 45, 3), False),
        ((3, 50, 4), False),
        ((3, 50, 7), True),
        ((3, 51, 2), False),
        ((3, 51, 3), True),
        ((3, 54, 1), True),
    ],
)
def test_runtime_recognizes_fixed_releases_and_backports(monkeypatch, version, patched):
    monkeypatch.setattr(sqlite3, "sqlite_version_info", version)
    monkeypatch.setattr(sqlite3, "sqlite_version", ".".join(map(str, version)))
    assert runtime_status()["sqlite_wal_reset_fixed"] is patched


def test_unsafe_runtime_cannot_create_state_and_doctor_can_explain_it(monkeypatch, tmp_path):
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 50, 4))
    monkeypatch.setattr(sqlite3, "sqlite_version", "3.50.4")
    directory = tmp_path / "state"
    with pytest.raises(GuardError, match="3.50.4") as error:
        Store(directory / "state.db", "test", create=True)
    assert error.value.code == "UNSUPPORTED_RUNTIME"
    with pytest.raises(GuardError):
        initialize(tmp_path, directory, "reviewer", RunnerConfig(argv=["unused"]))
    assert not directory.exists()
    for command in ("runtime", "doctor"):
        result = CliRunner().invoke(app, ["--root", str(tmp_path), command])
        assert result.exit_code == 1
        body = json.loads(result.stdout)
        assert body["ok"] is False
        assert body["runtime"]["sqlite_version"] == "3.50.4"
        assert body["runtime"]["next_action"]
    assert not directory.exists()
