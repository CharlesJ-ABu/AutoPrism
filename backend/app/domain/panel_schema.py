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


ALLOWED_UI_DSL_TYPES = frozenset({"stack", "metric", "table", "provenance"})


def validate_ui_dsl(
    schema: Mapping[str, Any],
    ui_dsl: Mapping[str, Any],
) -> tuple[SchemaIssue, ...]:
    """Validate the non-executable UI subset against the frozen data schema."""

    issues: list[SchemaIssue] = []
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
