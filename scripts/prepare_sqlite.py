"""Install a hash-verified SQLite in an isolated runtime; never touch global Python.

On Windows use a uv-managed Python under this checkout's .cache/python directory.
On Linux use a dynamically linked Python and set
LD_LIBRARY_PATH=<checkout>/.cache/sqlite/lib before launching Python.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "3.54.1"
RELEASE = "3540100"
ARCHIVES = {
    "win32": (
        f"sqlite-dll-win-x64-{RELEASE}.zip",
        "c2d09c8babb9399277055c057c97a53f1ffd7c5f11d0c1f2118ffdfa39f2daa4",
    ),
    "linux": (
        f"sqlite-amalgamation-{RELEASE}.zip",
        "92281c86e2957f9b9305890f9ac04204caa7b677cc868dc326d942689df28e30",
    ),
}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    base = Path(sys.base_prefix).resolve()
    if sys.platform == "win32" and not base.is_relative_to(root / ".cache" / "python"):
        raise SystemExit("Refusing to modify Python outside this checkout's .cache/python")
    if sys.platform not in ARCHIVES:
        raise SystemExit(
            "Preparation supports Windows x64 and Linux; supply a patched runtime elsewhere"
        )
    if sys.maxsize <= 2**32:
        raise SystemExit("Preparation requires a 64-bit runtime")
    if sys.platform == "win32" and platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("The pinned Windows library requires x64")
    name, expected = ARCHIVES[sys.platform]
    output = root / ".cache" / "sqlite"
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / name
    if not archive_path.exists():
        url = f"https://sqlite.org/2026/{name}"
        request = urllib.request.Request(url, headers={"User-Agent": "DecisionGuard-runtime-setup"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise SystemExit("SQLite archive exceeds expected size")
        if hashlib.sha3_256(data).hexdigest() != expected:
            raise SystemExit("SQLite archive SHA3-256 differs from the upstream published hash")
        archive_path.write_bytes(data)
    if hashlib.sha3_256(archive_path.read_bytes()).hexdigest() != expected:
        raise SystemExit("Cached SQLite archive failed SHA3-256 verification")
    with zipfile.ZipFile(archive_path) as archive:
        if sys.platform == "win32":
            library = base / "DLLs" / "sqlite3.dll"
            original = library.with_suffix(".dll.before-decisionguard")
            if not original.exists():
                shutil.copy2(library, original)
            library.write_bytes(archive.read("sqlite3.dll"))
        else:
            source = output / "sqlite3.c"
            source.write_bytes(archive.read(f"sqlite-amalgamation-{RELEASE}/sqlite3.c"))
            library = output / "lib" / "libsqlite3.so.0"
            library.parent.mkdir(exist_ok=True)
            subprocess.run(
                [
                    "cc",
                    "-O2",
                    "-fPIC",
                    "-shared",
                    "-DSQLITE_THREADSAFE=1",
                    "-DSQLITE_ENABLE_COLUMN_METADATA",
                    "-DSQLITE_ENABLE_FTS5",
                    "-DSQLITE_ENABLE_RTREE",
                    "-DSQLITE_ENABLE_MATH_FUNCTIONS",
                    "-Wl,-soname,libsqlite3.so.0",
                    str(source),
                    "-lm",
                    "-o",
                    str(library),
                ],
                check=True,
                timeout=180,
            )
    environment = os.environ.copy()
    if sys.platform == "linux":
        environment["LD_LIBRARY_PATH"] = str(library.parent)
    observed = subprocess.check_output(
        [sys.executable, "-c", "import sqlite3; print(sqlite3.sqlite_version)"],
        text=True,
        env=environment,
        timeout=15,
    ).strip()
    if observed != VERSION:
        raise SystemExit(f"Runtime still loads SQLite {observed}; expected {VERSION}")
    record = {
        "sqlite_version": observed,
        "archive": name,
        "archive_sha3_256": expected,
        "library_sha256": hashlib.sha256(library.read_bytes()).hexdigest(),
        "python_base": str(base),
        "library": str(library),
        "upstream": "https://sqlite.org/download.html",
    }
    (output / "runtime-provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
