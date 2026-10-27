"""Configured test command: python verify.py. Uses only a disposable loopback server."""

import pathlib
import shutil
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
node = shutil.which("node")
if node is None:
    raise SystemExit("Node 24 is required for the TypeScript fixture")
server = subprocess.Popen(
    [sys.executable, str(root / "api.py")],
    cwd=root,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
try:
    port = server.stdout.readline().strip()
    if not port.isdigit():
        raise RuntimeError("Loopback fixture server did not start")
    result = subprocess.run(
        [node, str(root / "client.mjs"), port],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    raise SystemExit(result.returncode)
finally:
    server.terminate()
    try:
        server.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)
    server.stdout.close()
    server.stderr.close()
