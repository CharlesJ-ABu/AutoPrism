from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


@dataclass(frozen=True)
class SchemaIssue:
    path: str
    message: str


def validate_panel_schema(schema: Mapping[str, Any]) -> tuple[SchemaIssue, ...]:
    issues: list[SchemaIssue] = []
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return (SchemaIssue("$", exc.message),)

    if schema.get("type") != "object":
        issues.append(SchemaIssue("$.type", "panel schema must describe an object"))
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        issues.append(
            SchemaIssue("$.properties", "panel schema requires at least one property")
        )
        properties = {}
    required = schema.get("required")
    if not isinstance(required, list):
        issues.append(SchemaIssue("$.required", "required must be an array"))

    metadata = schema.get("x-autoprism")
    if not isinstance(metadata, dict):
        issues.append(SchemaIssue("$.x-autoprism", "metadata object is required"))
    else:
        for key in (
            "time_dimension",
            "geographic_dimension",
            "aggregation",
            "visualization_mapping",
        ):
            if key not in metadata:
                issues.append(
                    SchemaIssue(f"$.x-autoprism.{key}", f"{key} is required")
                )

    for name, definition in properties.items():
        path = f"$.properties.{name}"
        if not isinstance(definition, dict) or "type" not in definition:
            issues.append(SchemaIssue(path, "property type is required"))
            continue
        if definition.get("type") in {"number", "integer"}:
            if "x-unit" not in definition and not definition.get("x-unitless"):
                issues.append(
                    SchemaIssue(path, "numeric properties require x-unit or x-unitless")
                )
    return tuple(issues)


def validate_panel_payload(
    schema: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> tuple[SchemaIssue, ...]:
    schema_issues = validate_panel_schema(schema)
    if schema_issues:
        return schema_issues
    validator = Draft202012Validator(schema)
    return tuple(
        SchemaIssue(
            "$" + "".join(f"[{part!r}]" for part in error.absolute_path),
            error.message,
        )
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    )
