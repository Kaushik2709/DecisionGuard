"""SQLite runtime checks, without opening or changing a project database."""

import platform
import sqlite3
from typing import Any

from decisionguard.domain.errors import require

SQLITE_WAL_ADVISORY = "https://sqlite.org/wal.html"
SQLITE_REQUIREMENT = "SQLite >=3.51.3, or patched 3.50.7+/3.44.6+ on those release branches"


def runtime_status() -> dict[str, Any]:
    version = sqlite3.sqlite_version_info
    patched = (
        version >= (3, 51, 3)
        or (version[:2] == (3, 50) and version >= (3, 50, 7))
        or (version[:2] == (3, 44) and version >= (3, 44, 6))
    )
    return {
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "sqlite_wal_reset_fixed": patched,
        "sqlite_requirement": SQLITE_REQUIREMENT,
        "sqlite_advisory": SQLITE_WAL_ADVISORY,
        "next_action": None
        if patched
        else "Use a Python distribution with patched SQLite; recreate the environment after stopping sessions",
    }


def require_safe_runtime() -> None:
    status = runtime_status()
    require(
        status["sqlite_wal_reset_fixed"],
        "UNSUPPORTED_RUNTIME",
        f"SQLite {status['sqlite_version']} is not a verified WAL-reset-fixed runtime. {SQLITE_REQUIREMENT}",
    )
