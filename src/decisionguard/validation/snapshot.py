import hashlib
import os
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from decisionguard.domain.errors import GuardError, require
from decisionguard.domain.models import ResourceLimits
from decisionguard.git.context import common_dir, safe_path, scoped_path


def git_names(
    root: Path, args: list[str], limits: ResourceLimits | None = None, deadline: float | None = None
) -> list[str]:
    """Bound the producer while enumerating, before allocating the whole listing."""
    limits = limits or ResourceLimits()
    deadline = deadline if deadline is not None else time.monotonic() + limits.snapshot_seconds
    require(time.monotonic() < deadline, "RESOURCE_LIMIT", "Snapshot time limit exceeded")
    process = subprocess.Popen(
        ["git", "-C", str(root), *args, "-z"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    names: list[str] = []
    errors: list[Exception] = []

    def read_names() -> None:
        assert process.stdout is not None
        buffered = b""
        consumed = 0
        try:
            while chunk := process.stdout.read(65536):
                consumed += len(chunk)
                require(
                    consumed <= limits.snapshot_name_bytes,
                    "RESOURCE_LIMIT",
                    "Source name byte limit exceeded",
                )
                require(
                    time.monotonic() < deadline, "RESOURCE_LIMIT", "Snapshot time limit exceeded"
                )
                parts = (buffered + chunk).split(b"\0")
                buffered = parts.pop()
                for part in parts:
                    if part:
                        require(
                            len(names) < limits.snapshot_files,
                            "RESOURCE_LIMIT",
                            "Snapshot path count exceeded",
                        )
                        names.append(part.decode("utf-8", errors="surrogateescape"))
            require(not buffered, "INVALID", "Incomplete Git source listing")
        except Exception as exc:
            errors.append(exc)
            if process.poll() is None:
                process.kill()

    reader = threading.Thread(target=read_names, daemon=True)
    reader.start()
    try:
        try:
            process.wait(timeout=max(0.001, min(30, deadline - time.monotonic())))
        except subprocess.TimeoutExpired as exc:
            raise GuardError(
                "RESOURCE_LIMIT", "Git source enumeration exceeded time limit"
            ) from exc
        reader.join(timeout=max(0.001, min(5, deadline - time.monotonic())))
        require(not reader.is_alive(), "RESOURCE_LIMIT", "Git source enumeration did not finish")
        if errors:
            raise errors[0]
        require(time.monotonic() < deadline, "RESOURCE_LIMIT", "Snapshot time limit exceeded")
        require(process.returncode == 0, "INVALID", "Cannot enumerate Git source")
        return names
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        reader.join(timeout=5)
        if not reader.is_alive() and process.stdout is not None:
            process.stdout.close()


def local_names(
    root: Path, exclusions: list[str], state: Path | None, limits: ResourceLimits, deadline: float
) -> list[str]:
    """Walk incrementally and prune excluded directories, with no recursive materialization."""
    stack: list[tuple[Iterator[os.DirEntry[str]], Callable[[], None]]] = []
    names: list[str] = []
    entries = name_bytes = 0

    def push(path: Path) -> None:
        iterator = os.scandir(path)
        stack.append((iterator, iterator.close))

    try:
        push(root)
        while stack:
            require(time.monotonic() < deadline, "RESOURCE_LIMIT", "Snapshot time limit exceeded")
            entry = next(stack[-1][0], None)
            if entry is None:
                stack.pop()[1]()
                continue
            name = Path(entry.path).relative_to(root).as_posix()
            if any(scoped_path(name, path) for path in exclusions):
                continue
            path = safe_path(root, name)
            if state is not None and path.is_relative_to(state):
                continue
            entries += 1
            name_bytes += len(name.encode("utf-8", errors="surrogateescape")) + 1
            require(
                entries <= limits.snapshot_files, "RESOURCE_LIMIT", "Snapshot path count exceeded"
            )
            require(
                name_bytes <= limits.snapshot_name_bytes,
                "RESOURCE_LIMIT",
                "Source name byte limit exceeded",
            )
            require(
                not entry.is_symlink(), "INVALID", "Symlinks are unsupported in source snapshots"
            )
            if entry.is_dir(follow_symlinks=False):
                push(path)
            else:
                require(entry.is_file(follow_symlinks=False), "INVALID", "Unsupported source type")
                names.append(name)
        require(time.monotonic() < deadline, "RESOURCE_LIMIT", "Snapshot time limit exceeded")
        return sorted(names)
    except OSError as exc:
        raise GuardError("SOURCE_CHANGED", "Cannot enumerate source snapshot") from exc
    finally:
        for _, close in reversed(stack):
            close()


def capture(
    root: Path, exclusions: list[str], state: Path, limits: ResourceLimits | None = None
) -> dict[str, Any]:
    limits = limits or ResourceLimits()
    deadline = time.monotonic() + limits.snapshot_seconds
    total = 0
    if common_dir(root):
        names = sorted(
            set(
                git_names(
                    root,
                    ["ls-files", "--cached", "--others", "--exclude-standard"],
                    limits,
                    deadline,
                )
            )
        )
    else:
        names = local_names(root, exclusions, state, limits, deadline)
    files: dict[str, str] = {}
    for name in names:
        require(time.monotonic() <= deadline, "RESOURCE_LIMIT", "Snapshot time limit exceeded")
        path = safe_path(root, name)
        if path.is_relative_to(state) or any(scoped_path(name, p) for p in exclusions):
            continue
        require(
            len(files) < limits.snapshot_files, "RESOURCE_LIMIT", "Snapshot file count exceeded"
        )
        require(
            not (root / name).is_symlink(),
            "INVALID",
            "Symlinks are unsupported in source snapshots",
        )
        try:
            if not path.exists():
                files[name] = "DELETED"
                continue
            require(path.is_file(), "INVALID", "Unsupported source type")
            require(
                path.stat().st_size <= limits.snapshot_file_bytes,
                "RESOURCE_LIMIT",
                "Snapshot file size exceeded",
            )
            hashed = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    total += len(chunk)
                    require(
                        size <= limits.snapshot_file_bytes and total <= limits.snapshot_total_bytes,
                        "RESOURCE_LIMIT",
                        "Snapshot byte limit exceeded",
                    )
                    require(
                        time.monotonic() <= deadline,
                        "RESOURCE_LIMIT",
                        "Snapshot time limit exceeded",
                    )
                    hashed.update(chunk)
            files[name] = hashed.hexdigest()
        except OSError as exc:
            raise GuardError("SOURCE_CHANGED", "Cannot read source snapshot") from exc
    from decisionguard.application.services import digest

    return {"digest": digest(files), "files": files}


def stable_capture(
    root: Path, exclusions: list[str], state: Path, limits: ResourceLimits | None = None
) -> dict[str, Any]:
    first = capture(root, exclusions, state, limits)
    second = capture(root, exclusions, state, limits)
    require(first == second, "SOURCE_CHANGED", "Source changed during capture")
    return second


def changed_paths(
    root: Path,
    baseline: str | None = None,
    limits: ResourceLimits | None = None,
    exclusions: list[str] | None = None,
    state: Path | None = None,
) -> list[str]:
    limits = limits or ResourceLimits()
    deadline = time.monotonic() + limits.snapshot_seconds
    if common_dir(root):
        # Include committed task edits as well as staged, unstaged, and untracked changes.
        return sorted(
            set(
                (
                    git_names(
                        root, ["diff", "--no-renames", baseline, "--name-only"], limits, deadline
                    )
                    if baseline
                    else git_names(root, ["ls-files", "--cached"], limits, deadline)
                )
                + git_names(root, ["ls-files", "--others", "--exclude-standard"], limits, deadline)
            )
        )
    return local_names(root, exclusions or [], state, limits, deadline)
