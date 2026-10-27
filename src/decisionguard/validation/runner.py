import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Any, cast

from decisionguard.domain.models import RunnerConfig
from decisionguard.git.context import safe_path


def execute(root: Path, config: RunnerConfig) -> dict[str, Any]:
    """Drain output continuously, retaining only bounded bytes; kill the process tree on timeout."""
    cwd = safe_path(root, config.cwd)
    output = bytearray()
    from decisionguard.validation.windows_job import WindowsJob

    job = WindowsJob() if os.name == "nt" else None
    try:
        return _execute(root, config, cwd, output, job)
    finally:
        if job:
            job.close()


def _execute(
    root: Path, config: RunnerConfig, cwd: Path, output: bytearray, job: Any
) -> dict[str, Any]:
    process = subprocess.Popen(
        config.argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        start_new_session=os.name != "nt",
        creationflags=(cast(Any, subprocess).CREATE_NEW_PROCESS_GROUP | 4) if job else 0,
    )
    assert process.stdout is not None

    def drain() -> None:
        assert process.stdout is not None
        while chunk := process.stdout.read(4096):
            remaining = config.output_limit - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])

    reader = threading.Thread(target=drain, daemon=True)
    timed_out = False
    try:
        if job:
            job.start(int(cast(Any, process)._handle), process.pid)
        reader.start()
        try:
            process.wait(timeout=config.timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
    finally:
        # Also clean up children when the parent succeeds or Python is interrupted.
        if job:
            job.close()
        else:
            try:
                cast(Any, os).killpg(process.pid, cast(Any, signal).SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        if reader.ident is not None:
            reader.join(timeout=5)
        if not reader.is_alive():
            process.stdout.close()
    reader.join(timeout=5)
    # A detached descendant holding the pipe must not hang the CLI indefinitely.
    return {
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "output": output.decode("utf-8", errors="replace"),
        "output_truncated": len(output) >= config.output_limit,
        "passed": process.returncode == 0 and not timed_out and not reader.is_alive(),
    }
