"""Process-owned advisory locks; an exited process cannot leave a stale owner."""

import ctypes
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from decisionguard.domain.errors import GuardError


@contextmanager
def exclusive_lock(path: Path, *, shared: bool = False) -> Iterator[None]:
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
                from ctypes import wintypes

                class Overlapped(ctypes.Structure):
                    _fields_ = [
                        ("internal", ctypes.c_size_t),
                        ("internal_high", ctypes.c_size_t),
                        ("offset", wintypes.DWORD),
                        ("offset_high", wintypes.DWORD),
                        ("event", wintypes.HANDLE),
                    ]

                api = cast(Any, ctypes).WinDLL("kernel32", use_last_error=True)
                api.LockFileEx.argtypes = [
                    wintypes.HANDLE,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    ctypes.POINTER(Overlapped),
                ]
                api.UnlockFileEx.argtypes = [
                    wintypes.HANDLE,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    ctypes.POINTER(Overlapped),
                ]
                overlap = Overlapped()
                handle = cast(Any, msvcrt).get_osfhandle(stream.fileno())
                if not api.LockFileEx(handle, 1 if shared else 3, 0, 1, 0, ctypes.byref(overlap)):
                    raise OSError("File lock is held")
            else:
                import fcntl

                api = cast(Any, fcntl)
                api.flock(stream.fileno(), (api.LOCK_SH if shared else api.LOCK_EX) | api.LOCK_NB)
        except OSError as exc:
            raise GuardError("BUSY", "Another administrative operation holds the lock") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                api.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(overlap))
            else:
                api = cast(Any, fcntl)
                api.flock(stream.fileno(), api.LOCK_UN)
