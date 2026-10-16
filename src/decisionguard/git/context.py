import subprocess
from pathlib import Path

from decisionguard.domain.errors import GuardError, require


def git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GuardError("OPERATIONAL", "Git operation exceeded timeout") from exc
    if result.returncode:
        raise GuardError(
            "INVALID", "Git operation failed: " + result.stderr.decode(errors="replace")
        )
    return result.stdout.decode("utf-8", errors="surrogateescape").strip()


def common_dir(root: Path) -> Path | None:
    try:
        return Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    except GuardError:
        return None


def repository_root(root: Path) -> Path:
    return Path(git(root, "rev-parse", "--show-toplevel")).resolve()


def safe_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    require(
        not candidate.is_absolute() and ".." not in candidate.parts,
        "INVALID",
        "Relative path required",
    )
    resolved = (root / candidate).resolve()
    require(resolved.is_relative_to(root.resolve()), "INVALID", "Path escapes project")
    return resolved


def scoped_path(path: str, scope: str) -> bool:
    normalized = Path(path).as_posix()
    prefix = Path(scope).as_posix().rstrip("/")
    return prefix == "." or normalized == prefix or normalized.startswith(prefix + "/")
