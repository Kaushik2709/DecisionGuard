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
    process = subprocess.Popen(
        config.argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        start_new_session=os.name != "nt",
        creationflags=cast(Any, subprocess).CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    assert process.stdout is not None

    def drain() -> None:
        assert process.stdout is not None
        while chunk := process.stdout.read(4096):
            remaining = config.output_limit - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    timed_out = False
    try:
        process.wait(timeout=config.timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
                check=False,
            )
        else:
            cast(Any, os).killpg(process.pid, cast(Any, signal).SIGKILL)
        process.kill()
        process.wait(timeout=10)
    reader.join(timeout=5)
    # A detached descendant holding the pipe must not hang the CLI indefinitely.
    return {
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "output": output.decode("utf-8", errors="replace"),
        "output_truncated": len(output) >= config.output_limit,
        "passed": process.returncode == 0 and not timed_out and not reader.is_alive(),
    }
