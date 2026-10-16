import sys
import time
from types import SimpleNamespace

import pytest

from decisionguard.domain.errors import GuardError
from decisionguard.domain.models import ResourceLimits
from decisionguard.validation import snapshot


@pytest.mark.parametrize("kind", ["count", "bytes"])
def test_git_listing_is_bounded_before_hashing(project, kind):
    _, root = project
    limits = ResourceLimits(**{"snapshot_files" if kind == "count" else "snapshot_name_bytes": 1})
    with pytest.raises(GuardError) as error:
        snapshot.git_names(root, ["ls-files", "--cached"], limits)
    assert error.value.code == "RESOURCE_LIMIT"


def test_non_git_walk_prunes_exclusions_and_state(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "code.py").write_text("value = 1\n")
    state = root / "state"
    state.mkdir()
    ignored = root / "generated"
    ignored.mkdir()
    for index in range(10):
        (state / str(index)).write_text("state")
        (ignored / str(index)).write_text("ignored")
    limits = ResourceLimits(snapshot_files=1)
    capture = snapshot.capture(root, ["generated"], state, limits)
    assert list(capture["files"]) == ["code.py"]
    assert snapshot.changed_paths(root, limits=limits, exclusions=["generated"], state=state) == [
        "code.py"
    ]


def test_non_git_empty_directory_traversal_is_bounded(tmp_path):
    for index in range(4):
        (tmp_path / str(index)).mkdir()
    with pytest.raises(GuardError) as error:
        snapshot.local_names(
            tmp_path, [], None, ResourceLimits(snapshot_files=2), time.monotonic() + 10
        )
    assert error.value.code == "RESOURCE_LIMIT"


def test_expired_capture_cannot_pass_with_empty_source(tmp_path, monkeypatch):
    times = iter([0.0, 2.0])
    monkeypatch.setattr(snapshot, "common_dir", lambda root: None)
    monkeypatch.setattr(snapshot, "time", SimpleNamespace(monotonic=lambda: next(times)))
    with pytest.raises(GuardError) as error:
        snapshot.capture(tmp_path, [], tmp_path / "state", ResourceLimits(snapshot_seconds=1))
    assert error.value.code == "RESOURCE_LIMIT"


def test_stalled_git_enumerator_is_terminated(tmp_path, monkeypatch):
    original = snapshot.subprocess.Popen
    children = []

    def stalled(*args, **kwargs):
        child = original([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(snapshot.subprocess, "Popen", stalled)
    with pytest.raises(GuardError) as error:
        snapshot.git_names(tmp_path, ["ls-files"], ResourceLimits(snapshot_seconds=0.1))
    assert error.value.code == "RESOURCE_LIMIT"
    assert len(children) == 1 and children[0].poll() is not None
