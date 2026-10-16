import pytest
from pydantic import ValidationError

from decisionguard.domain.compatibility import compare
from decisionguard.domain.models import TaskRequest, Value


@pytest.mark.parametrize(
    "kind,a,b,result",
    [
        ("money_unit", "INR.major.decimal-string", "INR.minor.integer", "incompatible"),
        ("time_unit", "seconds", "milliseconds", "incompatible"),
        ("auth", "required", "optional", "incompatible"),
        ("schema", "sha256:a", "sha256:b", "unknown"),
        ("error_format", "problem-json", "custom", "incompatible"),
        ("retry_policy", "none", "bounded", "incompatible"),
        ("idempotency", "required", "optional", "incompatible"),
        ("text", "event sourcing", "mutable rows", "unknown"),
        ("money_unit", "paise", "paise", "equal"),
    ],
)
def test_rules(kind, a, b, result):
    assert compare(Value(kind=kind, value=a), Value(kind=kind, value=b)) == result


def test_tombstone_conflicts():
    assert (
        compare(
            Value(kind="auth", value="required"), Value(kind="auth", value="required", deleted=True)
        )
        == "incompatible"
    )


def test_role_injection_rejected():
    with pytest.raises(ValidationError):
        TaskRequest(
            actor="agent",
            task_id="t",
            idempotency_key="k",
            worktree=".",
            paths=["."],
            role="coordinator",
        )
