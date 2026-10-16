"""Process-owned advisory locks; an exited process cannot leave a stale owner."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from decisionguard.domain.errors import GuardError


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                windows_api = cast(Any, msvcrt)
                windows_api.locking(stream.fileno(), windows_api.LK_NBLCK, 1)
            else:
                import fcntl

                api = cast(Any, fcntl)
                api.flock(stream.fileno(), api.LOCK_EX | api.LOCK_NB)
        except OSError as exc:
            raise GuardError("BUSY", "Another administrative operation holds the lock") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                windows_api = cast(Any, msvcrt)
                windows_api.locking(stream.fileno(), windows_api.LK_UNLCK, 1)
            else:
                api = cast(Any, fcntl)
                api.flock(stream.fileno(), api.LOCK_UN)
