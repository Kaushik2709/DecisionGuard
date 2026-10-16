from typing import Literal

from decisionguard.domain.models import Value


def compare(expected: Value, active: Value) -> Literal["equal", "incompatible", "unknown"]:
    if expected == active:
        return "equal"
    if expected.deleted or active.deleted:
        return "incompatible"
    if expected.kind != active.kind or expected.kind in {"schema", "text"}:
        return "unknown"
    return "incompatible"
