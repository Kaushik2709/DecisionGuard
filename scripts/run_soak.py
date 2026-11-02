"""Run an attended or managed disposable soak and retain running/final status."""

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from decisionguard.reports.reliability import soak
from decisionguard.storage.runtime import require_safe_runtime, runtime_status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=28800)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--history", type=int, default=10000)
    args = parser.parse_args()
    require_safe_runtime()
    report = args.report.resolve()
    if report.exists() or args.destination.exists():
        raise SystemExit("Report and disposable destination must both be new")
    report.parent.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    record = {
        "status": "running",
        "pid": os.getpid(),
        "python": sys.executable,
        "runtime": runtime_status(),
        "started_at": datetime.now(UTC).isoformat(),
        "requested_seconds": args.seconds,
        "workers": args.workers,
        "source_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / "src").rglob("*.py"))
        },
    }
    temporary = report.with_suffix(report.suffix + ".tmp")

    def save() -> None:
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        temporary.replace(report)

    save()
    try:
        result = soak(
            args.destination, seconds=args.seconds, workers=args.workers, history=args.history
        )
        record.update(status="completed" if result["passed"] else "failed", result=result)
    except BaseException as exc:
        record.update(status="failed", error=type(exc).__name__)
        raise
    finally:
        record["finished_at"] = datetime.now(UTC).isoformat()
        save()


if __name__ == "__main__":
    main()
