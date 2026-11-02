# Verified local runtime

DecisionGuard requires Python 3.11+ and a WAL-reset-fixed SQLite runtime: 3.51.3+
or the upstream 3.50.7+/3.44.6+ backports on those release branches. `decisionguard
runtime` checks this without opening project state. Unsafe versions are refused
before database creation/opening, migration or restoration. `doctor` explains the
runtime problem without opening an unsafe database.

The Python version alone does not determine SQLite safety. The project lockfile
cannot update the SQLite library bundled with Python. Supply a patched distribution,
or prepare an isolated workspace runtime with the checked-in helper. The helper uses
official SQLite 3.54.1 archives pinned by the SHA3-256 values published by upstream.
On Windows it refuses to modify Python outside this checkout's `.cache/python`
directory. On Linux it only builds a private library, without modifying Python.
Download/compilation requires network access and, on Linux, a C compiler.

## Windows x64 / PowerShell

```powershell
$env:UV_CACHE_DIR = "$PWD/.cache/uv"
$env:UV_PYTHON_INSTALL_DIR = "$PWD/.cache/python"
$env:UV_PROJECT_ENVIRONMENT = "$PWD/.cache/venv-patched"
uv python install 3.12.13 --no-bin --no-registry
uv sync --locked --group dev --python 3.12.13 --managed-python
uv run python scripts/prepare_sqlite.py
uv run decisionguard runtime
uv run decisionguard demo
```

The existing `.venv` and globally installed Python are preserved. The new executable
is `.cache/venv-patched/Scripts/python.exe`. Use that absolute executable when reviewing
a replacement MCP configuration. Stop old CLI/MCP sessions before switching clients;
all clients sharing a database must use a patched runtime. Replacing a running
runtime's DLL is unsupported. The helper retains the isolated runtime's original DLL
and writes `.cache/sqlite/runtime-provenance.json` with archive/library hashes.

## Linux x64

```sh
export UV_CACHE_DIR="$PWD/.cache/uv"
export UV_PROJECT_ENVIRONMENT="$PWD/.cache/venv-patched"
export LD_LIBRARY_PATH="$PWD/.cache/sqlite/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
uv sync --locked --group dev --python python3.12 --no-managed-python
uv run python scripts/prepare_sqlite.py
uv run decisionguard runtime
uv run decisionguard demo
```

Use an installed dynamically linked Python 3.11/3.12; Linux CI selects one through
the pinned official setup-python action. Some standalone Python builds statically
embed SQLite and cannot use this loader method.

The helper compiles the pinned official amalgamation into a private shared library
and verifies the SQLite version in a fresh Python process. Keep `LD_LIBRARY_PATH`
in the reviewed launch environment. A statically linked Python build that cannot
load the library fails verification; select a dynamically linked patched distribution.

Version checks recognize upstream releases/backports, not vendor-specific unversioned
patches. There is no bypass flag. See the [upstream WAL advisory](https://sqlite.org/wal.html)
and [archive hashes](https://sqlite.org/download.html).
