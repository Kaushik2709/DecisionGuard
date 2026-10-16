import sys
import threading
import time

import pytest
from conftest import accept, key, proposal

from decisionguard.application.services import Service
from decisionguard.application.validation import gate, validate
from decisionguard.domain.models import RunnerConfig, TaskMutation


def run(service, token=None):
    return validate(
        service, TaskMutation(actor="worker", task_id="worker", idempotency_key=token or key())
    )


@pytest.mark.parametrize("change", ["dirty", "untracked", "deleted"])
def test_source_change_invalidates(project, change):
    service, root = project
    run(service)
    assert gate(service, ["worker"])["receipt"]["passed"]
    if change == "dirty":
        (root / "code.py").write_text("amount='100.00'\n")
    elif change == "untracked":
        (root / "extra.py").write_text("unexpected = True\n")
    else:
        (root / "code.py").unlink()
    assert not gate(service, ["worker"])["receipt"]["passed"]


def test_validation_retry_does_not_execute_twice(project):
    service, root = project
    (root / "check.py").write_text(
        "from pathlib import Path\np=Path('runs.log')\np.write_text(p.read_text()+'x' if p.exists() else 'x')\n"
    )
    config = service.config.model_copy(update={"exclusions": ["runs.log"]})
    (service.directory / "config.json").write_text(config.model_dump_json())
    service = Service(service.directory)
    first = run(service, "same-run")
    second = run(service, "same-run")
    assert first == second
    assert (root / "runs.log").read_text() == "x"


@pytest.mark.parametrize("change", ["source", "decision", "config"])
def test_changes_during_execution_reject_evidence(project, change):
    service, root = project
    (root / "check.py").write_text(
        "import time\nfrom pathlib import Path\nPath('started').write_text('yes')\ntime.sleep(1)\n"
    )
    config = service.config.model_copy(update={"exclusions": ["started"]})
    (service.directory / "config.json").write_text(config.model_dump_json())
    service = Service(service.directory)
    results = []
    thread = threading.Thread(target=lambda: results.append(run(service)))
    thread.start()
    deadline = time.monotonic() + 10
    while not (root / "started").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert (root / "started").exists()
    if change == "source":
        (root / "code.py").write_text("amount='changed'\n")
    elif change == "decision":
        accept(service, proposal(service))
    else:
        config = config.model_copy(update={"exclusions": ["started", "different"]})
        (service.directory / "config.json").write_text(config.model_dump_json())
    thread.join(15)
    assert not thread.is_alive()
    assert not results[0]["run"]["valid"]


def test_failed_timeout_and_bounded_output(project):
    service, root = project
    (root / "check.py").write_text("print('failure')\nraise SystemExit(1)\n")
    assert not run(service)["run"]["passed"]
    config = service.config.model_copy(
        update={
            "runner": RunnerConfig(
                argv=[
                    sys.executable,
                    "-c",
                    "import time; print('x'*20000, flush=True); time.sleep(5)",
                ],
                timeout=1,
                output_limit=100,
            )
        }
    )
    (service.directory / "config.json").write_text(config.model_dump_json())
    result = run(Service(service.directory))["run"]
    assert result["timed_out"] and not result["passed"]
    assert len(result["output"]) <= 100


@pytest.mark.parametrize("committed", [False, True])
def test_unknown_changed_path_blocks_even_after_tests(project, committed):
    service, root = project
    (root / "foreign-contract.py").write_text("new = True\n")
    if committed:
        from decisionguard.git.context import git

        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-m",
            "Undeclared committed source",
        )
    assert run(service)["run"]["passed"]
    assert any(
        f["kind"] == "unknown_coverage" for f in gate(service, ["worker"])["receipt"]["findings"]
    )
