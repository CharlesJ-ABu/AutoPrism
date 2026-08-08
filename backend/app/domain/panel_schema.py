from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


@dataclass(frozen=True)
class SchemaIssue:
    path: str
    message: str


def validate_panel_schema(schema: Mapping[str, Any]) -> tuple[SchemaIssue, ...]:
    if not isinstance(schema, Mapping):
        return (SchemaIssue("$", "panel schema must be an object"),)
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
    issues = [
        SchemaIssue(
            "$" + "".join(f"[{part!r}]" for part in error.absolute_path),
            error.message,
        )
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    ]

    def reject_non_finite(value: Any, path: str) -> None:
        if isinstance(value, float) and not math.isfinite(value):
            issues.append(SchemaIssue(path, "numeric values must be finite"))
        elif isinstance(value, Mapping):
            for key, item in value.items():
                reject_non_finite(item, f"{path}[{key!r}]")
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                reject_non_finite(item, f"{path}[{index}]")

    reject_non_finite(payload, "$")
    return tuple(issues)


def validate_observation_contract(
    schema: Mapping[str, Any],
    *,
    metric_key: str,
    raw_value: Any,
    normalized_value: Any,
    unit: str | None,
    dimensions: Any,
) -> tuple[SchemaIssue, ...]:
    """Validate one INFO observation against its frozen panel schema."""

    issues = list(validate_panel_schema(schema))
    if issues:
        return tuple(issues)
    properties = schema["properties"]
    metric_definition = properties.get(metric_key)
    if not isinstance(metric_definition, dict) or metric_definition.get("type") not in {
        "number",
        "integer",
    }:
        issues.append(
            SchemaIssue("$.metric_key", "metric is not a numeric schema property")
        )
        return tuple(issues)
    for name, container in (
        ("raw_value", raw_value),
        ("normalized_value", normalized_value),
    ):
        if not isinstance(container, dict) or set(container) != {"value"}:
            issues.append(
                SchemaIssue(f"$.{name}", "must contain exactly one value field")
            )
            continue
        value = container["value"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or (isinstance(value, float) and not math.isfinite(value))
        ):
            issues.append(
                SchemaIssue(f"$.{name}.value", "must be a finite JSON number")
            )
    if raw_value != normalized_value:
        issues.append(
            SchemaIssue(
                "$.normalized_value",
                "must equal raw_value unless a deterministic conversion run exists",
            )
        )
    if isinstance(raw_value, dict) and set(raw_value) == {"value"}:
        try:
            Draft202012Validator(metric_definition).validate(raw_value["value"])
        except ValidationError as exc:
            issues.append(SchemaIssue("$.raw_value.value", exc.message))
    expected_unit = metric_definition.get("x-unit")
    if isinstance(expected_unit, str):
        if unit != expected_unit:
            issues.append(SchemaIssue("$.unit", f"must equal schema unit {expected_unit!r}"))
    elif metric_definition.get("x-unitless") is True:
        if unit is not None:
            issues.append(SchemaIssue("$.unit", "unitless metric must not declare a unit"))
    else:
        issues.append(SchemaIssue("$.unit", "numeric schema unit contract is invalid"))
    if not isinstance(dimensions, dict):
        issues.append(SchemaIssue("$.dimensions", "must be an object"))
        return tuple(issues)
    for key, value in dimensions.items():
        definition = properties.get(key)
        if not isinstance(definition, dict) or definition.get("type") not in {
            "string",
            "boolean",
        }:
            issues.append(
                SchemaIssue(
                    f"$.dimensions.{key}",
                    "dimension is not a string or boolean schema property",
                )
            )
            continue
        try:
            Draft202012Validator(definition).validate(value)
        except ValidationError as exc:
            issues.append(SchemaIssue(f"$.dimensions.{key}", exc.message))
    required_dimensions = {
        key
        for key in schema.get("required", [])
        if isinstance(properties.get(key), dict)
        and properties[key].get("type") in {"string", "boolean"}
    }
    missing_dimensions = required_dimensions - set(dimensions)
    if missing_dimensions:
        issues.append(
            SchemaIssue(
                "$.dimensions",
                "missing required dimensions: " + ", ".join(sorted(missing_dimensions)),
            )
        )
    return tuple(issues)


ALLOWED_UI_DSL_TYPES = frozenset({"stack", "metric", "table", "provenance"})


def validate_ui_dsl(
    schema: Mapping[str, Any],
    ui_dsl: Mapping[str, Any],
) -> tuple[SchemaIssue, ...]:
    """Validate the non-executable UI subset against the frozen data schema."""

    issues: list[SchemaIssue] = []
    if not isinstance(schema, Mapping):
        return (SchemaIssue("$.schema", "panel schema must be an object"),)
    if not isinstance(ui_dsl, Mapping):
        return (SchemaIssue("$.ui_dsl", "UI DSL root must be an object"),)
    properties = schema.get("properties")
    schema_properties = properties if isinstance(properties, dict) else {}

    def walk(node: Any, path: str, depth: int) -> None:
        if depth > 8:
            issues.append(SchemaIssue(path, "UI DSL nesting exceeds 8 levels"))
            return
        if not isinstance(node, dict):
            issues.append(SchemaIssue(path, "UI DSL node must be an object"))
            return
        node_type = node.get("type")
        if node_type not in ALLOWED_UI_DSL_TYPES:
            issues.append(
                SchemaIssue(
                    f"{path}.type",
                    f"unsupported UI DSL type: {node_type!r}",
                )
            )
            return
        if node_type == "stack":
            children = node.get("children")
            if not isinstance(children, list) or not children:
                issues.append(
                    SchemaIssue(f"{path}.children", "stack requires child nodes")
                )
                return
            for index, child in enumerate(children):
                walk(child, f"{path}.children[{index}]", depth + 1)
            return
        if "children" in node:
            issues.append(
                SchemaIssue(path, f"{node_type} nodes cannot contain children")
            )

        if node_type in {"metric", "table"}:
            field = node.get("field")
            if not isinstance(field, str) or not field:
                issues.append(
                    SchemaIssue(f"{path}.field", f"{node_type} requires a field")
                )
                return
            definition = schema_properties.get(field)
            if not isinstance(definition, dict):
                issues.append(
                    SchemaIssue(
                        f"{path}.field",
                        f"field {field!r} is not defined by the data schema",
                    )
                )
                return
            if node_type == "table":
                if definition.get("type") != "array":
                    issues.append(
                        SchemaIssue(
                            f"{path}.field",
                            "table field must reference an array property",
                        )
                    )
                columns = node.get("columns")
                if not isinstance(columns, list) or not columns or not all(
                    isinstance(column, str) and column for column in columns
                ):
                    issues.append(
                        SchemaIssue(
                            f"{path}.columns",
                            "table requires a non-empty string column list",
                        )
                    )
                else:
                    items = definition.get("items")
                    item_properties = (
                        items.get("properties", {})
                        if isinstance(items, dict)
                        else {}
                    )
                    for column in columns:
                        if column not in item_properties:
                            issues.append(
                                SchemaIssue(
                                    f"{path}.columns",
                                    f"column {column!r} is not defined by array items",
                                )
                            )

    walk(ui_dsl, "$.ui_dsl", 0)
    return tuple(issues)
