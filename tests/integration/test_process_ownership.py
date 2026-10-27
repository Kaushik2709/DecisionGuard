import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from decisionguard.domain.models import RunnerConfig
from decisionguard.validation.runner import execute


def alive(pid):
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.restype = ctypes.c_void_p
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = api.OpenProcess(0x100000, False, pid)
        if not handle:
            return False
        try:
            return api.WaitForSingleObject(handle, 0) == 0x102
        finally:
            api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")
    return not (stat.exists() and stat.read_text().split(")", 1)[1].strip().startswith("Z"))


@pytest.mark.parametrize("parent_waits", [False, True])
def test_descendant_cleanup_after_parent_exit_or_timeout(tmp_path, parent_waits):
    (tmp_path / "parent.py").write_text(
        "import subprocess,sys,time\nfrom pathlib import Path\n"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
        "Path('child.pid').write_text(str(child.pid))\n"
        + ("time.sleep(60)\n" if parent_waits else "")
    )
    outcome = execute(tmp_path, RunnerConfig(argv=[sys.executable, "parent.py"], timeout=2))
    child = int((tmp_path / "child.pid").read_text())
    for _ in range(30):
        if not alive(child):
            break
        time.sleep(0.05)
    assert not alive(child)
    assert outcome["timed_out"] == parent_waits
    assert outcome["passed"] == (not parent_waits)


def test_keyboard_interrupt_cleans_process(tmp_path, monkeypatch):
    original_wait = subprocess.Popen.wait
    seen = []

    def interrupted(process, *args, **kwargs):
        if not seen:
            seen.append(process)
            raise KeyboardInterrupt()
        return original_wait(process, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "wait", interrupted)
    with pytest.raises(KeyboardInterrupt):
        execute(tmp_path, RunnerConfig(argv=[sys.executable, "-c", "import time; time.sleep(60)"]))
    assert seen[0].poll() is not None
