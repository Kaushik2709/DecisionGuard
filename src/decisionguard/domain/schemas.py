"""Conservative JSON-schema containment for an explicitly supported finite subset."""

import json
from typing import Any, Literal

Result = Literal["equal", "incompatible", "unknown"]
ANNOTATIONS = {"title", "description", "default", "examples", "example", "$comment", "deprecated"}
SUPPORTED = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
} | ANNOTATIONS
TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}


def issues(schema: Any, pointer: str = "", depth: int = 0) -> list[dict[str, str]]:
    if depth > 64:
        return [{"pointer": pointer, "reason": "Schema depth exceeds 64"}]
    if not isinstance(schema, dict):
        return [{"pointer": pointer, "reason": "Only object schemas are supported"}]
    result = [
        {"pointer": pointer + "/" + k, "reason": "Unsupported schema keyword"}
        for k in schema.keys() - SUPPORTED
    ]
    kinds = schema.get("type")
    kinds = kinds if isinstance(kinds, list) else [kinds]
    if not kinds or any(not isinstance(k, str) or k not in TYPES for k in kinds):
        result.append({"pointer": pointer, "reason": "Explicit supported type required"})
        return result
    if len(kinds) > 1 and not (len(kinds) == 2 and "null" in kinds):
        result.append({"pointer": pointer, "reason": "Only nullable type unions are supported"})
    if "enum" in schema and (
        not isinstance(schema["enum"], list)
        or not schema["enum"]
        or any(isinstance(v, (dict, list)) for v in schema["enum"])
    ):
        result.append({"pointer": pointer, "reason": "Only nonempty scalar enums are supported"})
    if "object" in kinds:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if (
            not isinstance(properties, dict)
            or not isinstance(required, list)
            or any(not isinstance(k, str) or k not in properties for k in required)
            or not isinstance(schema.get("additionalProperties", True), bool)
        ):
            result.append({"pointer": pointer, "reason": "Unsupported object constraints"})
        else:
            for key, value in properties.items():
                result.extend(issues(value, pointer + "/properties/" + escape(key), depth + 1))
    if "array" in kinds:
        result.extend(issues(schema.get("items"), pointer + "/items", depth + 1))
    # Keywords applied to the wrong instance type are ambiguous for this subset.
    for key, kind in [
        ("properties", "object"),
        ("required", "object"),
        ("additionalProperties", "object"),
        ("items", "array"),
    ]:
        if key in schema and kind not in kinds:
            result.append({"pointer": pointer + "/" + key, "reason": "Keyword/type mismatch"})
    return result


def escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def types(schema: dict[str, Any]) -> set[str]:
    value = schema["type"]
    return set(value if isinstance(value, list) else [value])


def scalar_valid(value: Any, schema: dict[str, Any]) -> bool:
    kind = (
        "null"
        if value is None
        else "boolean"
        if isinstance(value, bool)
        else "integer"
        if isinstance(value, int)
        else "number"
        if isinstance(value, float)
        else "string"
        if isinstance(value, str)
        else "other"
    )
    allowed = types(schema)
    return (kind in allowed or kind == "integer" and "number" in allowed) and (
        "enum" not in schema or any(type(value) is type(v) and value == v for v in schema["enum"])
    )


def subset(left: dict[str, Any], right: dict[str, Any], pointer: str = "") -> list[dict[str, str]]:
    """Return reasons the left language is not proven a subset of the right language."""
    result: list[dict[str, str]] = []

    def add(reason: str, path: str = pointer) -> None:
        result.append({"pointer": path, "reason": reason})

    if "enum" in left:
        if all(scalar_valid(v, right) for v in left["enum"] if scalar_valid(v, left)):
            return []
        add("A previously permitted value is no longer permitted")
        return result
    lt, rt = types(left), types(right)
    if not all(t in rt or t == "integer" and "number" in rt for t in lt):
        add("Incompatible type or nullability")
    if "enum" in right:
        add("Unbounded values cannot satisfy the enum restriction")
    if "object" in lt and "object" in rt:
        lp, rp = left.get("properties", {}), right.get("properties", {})
        if not set(right.get("required", [])).issubset(left.get("required", [])):
            add("Required fields are not guaranteed", pointer + "/required")
        la, ra = left.get("additionalProperties", True), right.get("additionalProperties", True)
        if la and not ra:
            add(
                "Additional fields may be produced but are forbidden",
                pointer + "/additionalProperties",
            )
        for key, value in lp.items():
            path = pointer + "/properties/" + escape(key)
            if key in rp:
                result.extend(subset(value, rp[key], path))
            elif not ra:
                add("Field is forbidden by the receiving contract", path)
        if la:
            for key in rp.keys() - lp.keys():
                add(
                    "Unconstrained additional field cannot satisfy the receiving type",
                    pointer + "/properties/" + escape(key),
                )
    if "array" in lt and "array" in rt:
        result.extend(subset(left["items"], right["items"], pointer + "/items"))
    return result


def compare_artifacts(
    expected: dict[str, Any], active: dict[str, Any]
) -> tuple[Result, list[dict[str, str]]]:
    if active.get("missing") or any(
        expected.get(k) != active.get(k) for k in ("method", "path", "status")
    ):
        return "incompatible", [{"pointer": "", "reason": "Operation removed or relocated"}]
    if expected.get("direction") != active.get("direction"):
        return "unknown", [{"pointer": "", "reason": "Contract direction changed"}]
    if expected.get("unsupported") or active.get("unsupported"):
        return "unknown", expected.get("unsupported", []) + active.get("unsupported", [])
    if active["direction"] == "security":
        return (
            ("equal", [])
            if expected["schema"] == active["schema"]
            else (
                "incompatible",
                [{"pointer": "/security", "reason": "Authentication requirements changed"}],
            )
        )
    a, b = expected["schema"], active["schema"]
    unsupported = issues(a) + issues(b)
    if unsupported:
        return "unknown", unsupported
    # Requests: new producer accepts all old client inputs.
    # Responses: new producer emits only what the old consumer permits.
    problems = subset(a, b) if active["direction"] == "request" else subset(b, a)
    if active["direction"] == "request" and active.get("required") and not expected.get("required"):
        problems.append(
            {"pointer": "/requestBody/required", "reason": "Request body is now mandatory"}
        )
    return ("incompatible" if problems else "equal"), problems


def normalized(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )
