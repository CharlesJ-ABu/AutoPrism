from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import math
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from app.domain.numeric import UNIT_REGISTRY, decimal_value


@dataclass(frozen=True)
class SchemaIssue:
    path: str
    message: str


GEO_SCOPE_CONTRACT_VERSION = "geo-scope-v1"
TIME_SCOPE_CONTRACT_VERSION = "time-scope-v1"
MAP_DISPLAY_TYPES = frozenset(
    {
        "MARKER",
        "HOTSPOT",
        "RIPPLE",
        "FLOW",
        "COMPARISON",
        "SHIELD_UP",
        "ZONE",
    }
)
POINT_DISPLAY_TYPES = frozenset({"MARKER", "HOTSPOT", "RIPPLE"})
LINE_DISPLAY_TYPES = frozenset({"FLOW", "COMPARISON", "SHIELD_UP"})


def _validate_temporal_mapping(
    mapping: Any,
    *,
    properties: Mapping[str, Any],
    required: set[str],
) -> tuple[SchemaIssue, ...]:
    if not isinstance(mapping, Mapping):
        # Legacy panels may keep a descriptive string, but it has no executable
        # time authority for currency conversion or trusted derivation.
        return ()
    path = "$.x-autoprism.time_dimension"
    issues: list[SchemaIssue] = []
    if set(mapping) - {"contract_version", "kind", "field", "start_field", "end_field"}:
        issues.append(SchemaIssue(path, "time contract contains unsupported keys"))
    if mapping.get("contract_version") != TIME_SCOPE_CONTRACT_VERSION:
        issues.append(
            SchemaIssue(
                f"{path}.contract_version",
                f"must equal {TIME_SCOPE_CONTRACT_VERSION!r}",
            )
        )
    kind = mapping.get("kind")
    if kind not in {"instant", "period_end", "period_average"}:
        issues.append(SchemaIssue(f"{path}.kind", "unsupported time basis"))
        return tuple(issues)
    keys = ["field"] if kind in {"instant", "period_end"} else ["start_field", "end_field"]
    for key in keys:
        field = mapping.get(key)
        definition = properties.get(field) if isinstance(field, str) else None
        if not isinstance(field, str) or not isinstance(definition, Mapping):
            issues.append(SchemaIssue(f"{path}.{key}", "must name a schema field"))
        elif definition.get("type") != "string":
            issues.append(SchemaIssue(f"{path}.{key}", "time field must be a string"))
        elif field not in required:
            issues.append(SchemaIssue(f"{path}.{key}", "time field must be required"))
    return tuple(issues)


def temporal_source_fields(schema: Mapping[str, Any]) -> tuple[str, ...]:
    metadata = schema.get("x-autoprism")
    mapping = metadata.get("time_dimension") if isinstance(metadata, Mapping) else None
    if (
        not isinstance(mapping, Mapping)
        or mapping.get("contract_version") != TIME_SCOPE_CONTRACT_VERSION
    ):
        return ()
    kind = mapping.get("kind")
    keys = ("field",) if kind in {"instant", "period_end"} else ("start_field", "end_field")
    return tuple(
        field for field in (mapping.get(key) for key in keys) if isinstance(field, str)
    )


def _utc_naive(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("time scope fields must be ISO-8601 strings")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("time scope fields must be ISO-8601 strings") from exc
    if parsed.tzinfo is None:
        raise ValueError("time scope fields must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def build_temporal_scope(
    schema: Mapping[str, Any],
    data: Mapping[str, Any],
) -> dict[str, datetime | None]:
    result: dict[str, datetime | None] = {
        "observed_at": None,
        "period_start": None,
        "period_end": None,
    }
    metadata = schema.get("x-autoprism")
    mapping = metadata.get("time_dimension") if isinstance(metadata, Mapping) else None
    if not isinstance(mapping, Mapping):
        return result
    if mapping.get("contract_version") != TIME_SCOPE_CONTRACT_VERSION:
        raise ValueError("time scope contract version is unsupported")
    kind = mapping.get("kind")
    if kind == "instant":
        result["observed_at"] = _utc_naive(data.get(mapping.get("field")))
    elif kind == "period_end":
        result["period_end"] = _utc_naive(data.get(mapping.get("field")))
    elif kind == "period_average":
        start = _utc_naive(data.get(mapping.get("start_field")))
        end = _utc_naive(data.get(mapping.get("end_field")))
        if start > end:
            raise ValueError("period start must not be after period end")
        result["period_start"], result["period_end"] = start, end
    else:
        raise ValueError("time scope basis is unsupported")
    return result


def _validate_geographic_mapping(
    mapping: Any,
    *,
    properties: Mapping[str, Any],
    required: set[str],
) -> tuple[SchemaIssue, ...]:
    if not isinstance(mapping, Mapping):
        # Legacy panels use a descriptive string such as "US" or "market".
        # It is valid panel metadata, but it is not executable map authority.
        return ()
    issues: list[SchemaIssue] = []
    path = "$.x-autoprism.geographic_dimension"
    allowed = {
        "contract_version",
        "display_type",
        "label_field",
        "latitude_field",
        "longitude_field",
        "end_latitude_field",
        "end_longitude_field",
        "polygon_field",
    }
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        issues.append(
            SchemaIssue(path, "unsupported geographic keys: " + ", ".join(unknown))
        )
    if mapping.get("contract_version") != GEO_SCOPE_CONTRACT_VERSION:
        issues.append(
            SchemaIssue(
                f"{path}.contract_version",
                f"must equal {GEO_SCOPE_CONTRACT_VERSION!r}",
            )
        )
    display_type = mapping.get("display_type")
    if display_type not in MAP_DISPLAY_TYPES:
        issues.append(
            SchemaIssue(
                f"{path}.display_type",
                "must be an allowlisted map display type",
            )
        )

    fields: list[tuple[str, str, str | None]] = [
        ("label_field", "string", None),
    ]
    if display_type in POINT_DISPLAY_TYPES | LINE_DISPLAY_TYPES:
        fields.extend(
            [
                ("latitude_field", "number", "degree_latitude"),
                ("longitude_field", "number", "degree_longitude"),
            ]
        )
    if display_type in LINE_DISPLAY_TYPES:
        fields.extend(
            [
                ("end_latitude_field", "number", "degree_latitude"),
                ("end_longitude_field", "number", "degree_longitude"),
            ]
        )
    if display_type == "ZONE":
        fields.append(("polygon_field", "array", None))

    for mapping_key, expected_type, expected_unit in fields:
        field = mapping.get(mapping_key)
        field_path = f"{path}.{mapping_key}"
        if not isinstance(field, str) or not field:
            issues.append(SchemaIssue(field_path, "must name a schema field"))
            continue
        definition = properties.get(field)
        if not isinstance(definition, Mapping):
            issues.append(
                SchemaIssue(field_path, f"field {field!r} is absent from properties")
            )
            continue
        actual_type = definition.get("type")
        type_matches = (
            actual_type in {"number", "integer"}
            if expected_type == "number"
            else actual_type == expected_type
        )
        if not type_matches:
            issues.append(
                SchemaIssue(field_path, f"field {field!r} must be {expected_type}")
            )
        if expected_unit is not None and definition.get("x-unit") != expected_unit:
            issues.append(
                SchemaIssue(
                    field_path,
                    f"field {field!r} must declare x-unit {expected_unit!r}",
                )
            )
        if field not in required:
            issues.append(
                SchemaIssue(field_path, f"field {field!r} must be required")
            )
    return tuple(issues)


def geographic_source_fields(schema: Mapping[str, Any]) -> tuple[str, ...]:
    metadata = schema.get("x-autoprism")
    mapping = metadata.get("geographic_dimension") if isinstance(metadata, Mapping) else None
    if not isinstance(mapping, Mapping):
        return ()
    display_type = mapping.get("display_type")
    keys = ["label_field"]
    if display_type in POINT_DISPLAY_TYPES | LINE_DISPLAY_TYPES:
        keys.extend(["latitude_field", "longitude_field"])
    if display_type in LINE_DISPLAY_TYPES:
        keys.extend(["end_latitude_field", "end_longitude_field"])
    if display_type == "ZONE":
        keys.append("polygon_field")
    fields = [mapping.get(key) for key in keys]
    return tuple(dict.fromkeys(field for field in fields if isinstance(field, str)))


def _coordinate(value: Any, *, latitude: bool) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("map coordinates must be finite JSON numbers")
    parsed = decimal_value(value)
    lower, upper = (Decimal("-90"), Decimal("90")) if latitude else (
        Decimal("-180"),
        Decimal("180"),
    )
    if parsed < lower or parsed > upper:
        raise ValueError(
            "latitude must be between -90 and 90"
            if latitude
            else "longitude must be between -180 and 180"
        )
    return parsed


def build_geographic_scope(
    schema: Mapping[str, Any],
    data: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a canonical, evidence-bound GeoJSON scope from frozen panel data."""

    metadata = schema.get("x-autoprism")
    mapping = metadata.get("geographic_dimension") if isinstance(metadata, Mapping) else None
    if not isinstance(mapping, Mapping):
        return {}
    display_type = mapping.get("display_type")
    label_field = mapping.get("label_field")
    label = data.get(label_field) if isinstance(label_field, str) else None
    if not isinstance(label, str) or not label.strip():
        raise ValueError("geographic label must be a non-empty source string")

    source_fields = {
        key.removesuffix("_field"): mapping[key]
        for key in (
            "label_field",
            "latitude_field",
            "longitude_field",
            "end_latitude_field",
            "end_longitude_field",
            "polygon_field",
        )
        if isinstance(mapping.get(key), str)
    }
    if display_type in POINT_DISPLAY_TYPES | LINE_DISPLAY_TYPES:
        latitude = _coordinate(data.get(mapping.get("latitude_field")), latitude=True)
        longitude = _coordinate(data.get(mapping.get("longitude_field")), latitude=False)
        if display_type in LINE_DISPLAY_TYPES:
            end_latitude = _coordinate(
                data.get(mapping.get("end_latitude_field")), latitude=True
            )
            end_longitude = _coordinate(
                data.get(mapping.get("end_longitude_field")), latitude=False
            )
            geometry: dict[str, Any] = {
                "type": "LineString",
                "coordinates": [
                    [longitude, latitude],
                    [end_longitude, end_latitude],
                ],
            }
        else:
            geometry = {
                "type": "Point",
                "coordinates": [longitude, latitude],
            }
    elif display_type == "ZONE":
        polygon_field = mapping.get("polygon_field")
        raw_ring = data.get(polygon_field) if isinstance(polygon_field, str) else None
        if not isinstance(raw_ring, list) or len(raw_ring) < 4:
            raise ValueError("map polygon must contain at least four positions")
        ring: list[list[Decimal]] = []
        for position in raw_ring:
            if not isinstance(position, (list, tuple)) or len(position) != 2:
                raise ValueError("map polygon positions must be [longitude, latitude]")
            ring.append(
                [
                    _coordinate(position[0], latitude=False),
                    _coordinate(position[1], latitude=True),
                ]
            )
        if ring[0] != ring[-1]:
            raise ValueError("map polygon ring must be closed")
        if len(ring) > 500:
            raise ValueError("map polygon exceeds the 500-position limit")
        geometry = {"type": "Polygon", "coordinates": [ring]}
    else:
        raise ValueError("map display type is not supported")

    return {
        "contract_version": GEO_SCOPE_CONTRACT_VERSION,
        "display_type": display_type,
        "label": label.strip(),
        "geometry": geometry,
        "source_fields": source_fields,
    }


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
        required_fields: set[str] = set()
    else:
        required_fields = {item for item in required if isinstance(item, str)}

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
        if "geographic_dimension" in metadata:
            issues.extend(
                _validate_geographic_mapping(
                    metadata["geographic_dimension"],
                    properties=properties,
                    required=required_fields,
                )
            )
        if "time_dimension" in metadata:
            issues.extend(
                _validate_temporal_mapping(
                    metadata["time_dimension"],
                    properties=properties,
                    required=required_fields,
                )
            )

    for name, definition in properties.items():
        path = f"$.properties.{name}"
        if not isinstance(definition, dict) or "type" not in definition:
            issues.append(SchemaIssue(path, "property type is required"))
            continue
        if definition.get("type") in {"number", "integer"}:
            has_unit = isinstance(definition.get("x-unit"), str)
            is_unitless = definition.get("x-unitless") is True
            if has_unit == is_unitless:
                issues.append(
                    SchemaIssue(
                        path,
                        "numeric properties require exactly one of x-unit or x-unitless",
                    )
                )
            if has_unit and definition["x-unit"] not in UNIT_REGISTRY:
                issues.append(SchemaIssue(path, "x-unit is absent from the frozen registry"))
            currency = definition.get("x-currency")
            if currency is not None and (
                not isinstance(currency, str)
                or len(currency) != 3
                or currency.upper() != currency
            ):
                issues.append(SchemaIssue(path, "x-currency must be a three-letter uppercase code"))
            uncertainty = definition.get("x-uncertainty", {"kind": "unknown"})
            if not isinstance(uncertainty, dict):
                issues.append(SchemaIssue(path, "x-uncertainty must be an object"))
                continue
            uncertainty_kind = uncertainty.get("kind")
            if uncertainty_kind not in {"exact", "source_absolute_field", "unknown"}:
                issues.append(SchemaIssue(path, "x-uncertainty kind is unsupported"))
            if uncertainty_kind == "source_absolute_field":
                error_field = uncertainty.get("field")
                error_definition = properties.get(error_field)
                if (
                    not isinstance(error_field, str)
                    or not isinstance(error_definition, dict)
                    or error_definition.get("type") not in {"number", "integer"}
                ):
                    issues.append(
                        SchemaIssue(path, "uncertainty field must name a numeric property")
                    )
                elif error_field not in required_fields:
                    issues.append(SchemaIssue(path, "uncertainty field must be required"))
            elif set(uncertainty) != {"kind"}:
                issues.append(SchemaIssue(path, "x-uncertainty contains unsupported keys"))
    return tuple(issues)


def numeric_uncertainty_contract(
    definition: Mapping[str, Any],
    data: Mapping[str, Any],
) -> tuple[str, Any | None, dict[str, Any]]:
    """Resolve a schema-declared uncertainty without inventing a default error."""

    uncertainty = definition.get("x-uncertainty", {"kind": "unknown"})
    if not isinstance(uncertainty, Mapping):
        raise ValueError("numeric uncertainty contract must be an object")
    kind = uncertainty.get("kind", "unknown")
    if kind == "exact":
        return "exact", 0, {"kind": "schema_exact"}
    if kind == "unknown":
        return "unknown", None, {"kind": "schema_unknown"}
    if kind != "source_absolute_field":
        raise ValueError("numeric uncertainty kind is unsupported")
    field = uncertainty.get("field")
    if not isinstance(field, str) or field not in data:
        raise ValueError("source uncertainty field is missing")
    error = decimal_value(data[field])
    if error < 0:
        raise ValueError("source absolute uncertainty must not be negative")
    return (
        "bounded",
        error,
        {"kind": "source_absolute_field", "field": field},
    )


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
        if (
            isinstance(value, Decimal)
            and not value.is_finite()
        ) or (isinstance(value, float) and not math.isfinite(value)):
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
            or not isinstance(value, (int, float, Decimal))
            or (isinstance(value, Decimal) and not value.is_finite())
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


ALLOWED_UI_DSL_TYPES = frozenset(
    {"stack", "metric", "table", "chart", "timeline", "provenance"}
)


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
            unknown = set(node) - {"type", "version", "children"}
            if unknown:
                issues.append(
                    SchemaIssue(path, "stack contains unsupported properties")
                )
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

        if node_type in {"metric", "table", "chart", "timeline"}:
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
            if node_type in {"table", "chart", "timeline"}:
                if definition.get("type") != "array":
                    issues.append(
                        SchemaIssue(
                            f"{path}.field",
                            f"{node_type} field must reference an array property",
                        )
                    )
                    return
                items = definition.get("items")
                item_properties = (
                    items.get("properties", {}) if isinstance(items, dict) else {}
                )
            else:
                item_properties = {}

            if node_type == "metric":
                if definition.get("type") not in {"number", "integer"}:
                    issues.append(
                        SchemaIssue(f"{path}.field", "metric field must be numeric")
                    )
                declared_unit = node.get("unit")
                schema_unit = definition.get("x-unit")
                if declared_unit is not None and declared_unit != schema_unit:
                    issues.append(
                        SchemaIssue(
                            f"{path}.unit",
                            "metric unit must equal the frozen Schema x-unit",
                        )
                    )
                if set(node) - {"type", "field", "label", "unit"}:
                    issues.append(
                        SchemaIssue(path, "metric contains unsupported properties")
                    )

            if node_type == "table":
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
                    for column in columns:
                        if column not in item_properties:
                            issues.append(
                                SchemaIssue(
                                    f"{path}.columns",
                                    f"column {column!r} is not defined by array items",
                                )
                            )
                page_size = node.get("page_size", 20)
                if (
                    isinstance(page_size, bool)
                    or not isinstance(page_size, int)
                    or not 1 <= page_size <= 100
                ):
                    issues.append(
                        SchemaIssue(
                            f"{path}.page_size",
                            "must be an integer from 1 to 100",
                        )
                    )
                if set(node) - {"type", "field", "columns", "page_size"}:
                    issues.append(
                        SchemaIssue(path, "table contains unsupported properties")
                    )

            if node_type == "chart":
                variant = node.get("variant")
                if variant not in {"line", "bar", "area"}:
                    issues.append(
                        SchemaIssue(f"{path}.variant", "chart variant must be line, bar or area")
                    )
                for key, numeric in (("x_field", False), ("y_field", True)):
                    item_field = node.get(key)
                    item_definition = (
                        item_properties.get(item_field)
                        if isinstance(item_field, str)
                        else None
                    )
                    if not isinstance(item_definition, dict):
                        issues.append(
                            SchemaIssue(f"{path}.{key}", "must name an array-item field")
                        )
                        continue
                    allowed_types = (
                        {"number", "integer"}
                        if numeric
                        else {"string", "number", "integer"}
                    )
                    if item_definition.get("type") not in allowed_types:
                        issues.append(
                            SchemaIssue(
                                f"{path}.{key}",
                                "field type is incompatible with chart axis",
                            )
                        )
                    if numeric:
                        has_unit = isinstance(item_definition.get("x-unit"), str)
                        unitless = item_definition.get("x-unitless") is True
                        if has_unit == unitless:
                            issues.append(
                                SchemaIssue(
                                    f"{path}.{key}",
                                    "numeric chart axis requires x-unit or x-unitless",
                                )
                            )
                max_points = node.get("max_points", 80)
                if (
                    isinstance(max_points, bool)
                    or not isinstance(max_points, int)
                    or not 2 <= max_points <= 200
                ):
                    issues.append(
                        SchemaIssue(
                            f"{path}.max_points",
                            "must be an integer from 2 to 200",
                        )
                    )
                if set(node) - {
                    "type", "field", "variant", "x_field", "y_field",
                    "label", "max_points",
                }:
                    issues.append(
                        SchemaIssue(path, "chart contains unsupported properties")
                    )

            if node_type == "timeline":
                for key in ("time_field", "title_field"):
                    item_field = node.get(key)
                    item_definition = (
                        item_properties.get(item_field)
                        if isinstance(item_field, str)
                        else None
                    )
                    if (
                        not isinstance(item_definition, dict)
                        or item_definition.get("type") != "string"
                    ):
                        issues.append(
                            SchemaIssue(f"{path}.{key}", "must name a string array-item field")
                        )
                    elif key == "time_field" and item_definition.get("format") != "date-time":
                        issues.append(
                            SchemaIssue(
                                f"{path}.{key}",
                                "timeline time field requires date-time format",
                            )
                        )
                value_field = node.get("value_field")
                if value_field is not None:
                    value_definition = item_properties.get(value_field)
                    if (
                        not isinstance(value_definition, dict)
                        or value_definition.get("type") not in {"number", "integer"}
                    ):
                        issues.append(
                            SchemaIssue(
                                f"{path}.value_field",
                                "must name a numeric array-item field",
                            )
                        )
                max_items = node.get("max_items", 20)
                if (
                    isinstance(max_items, bool)
                    or not isinstance(max_items, int)
                    or not 1 <= max_items <= 100
                ):
                    issues.append(
                        SchemaIssue(f"{path}.max_items", "must be an integer from 1 to 100")
                    )
                if set(node) - {
                    "type", "field", "time_field", "title_field",
                    "value_field", "label", "max_items",
                }:
                    issues.append(
                        SchemaIssue(path, "timeline contains unsupported properties")
                    )

        if node_type == "provenance":
            allowed = {
                "type",
                "show_source",
                "show_locator",
                "show_retrieved_at",
                "show_artifact_hash",
            }
            if set(node) - allowed:
                issues.append(
                    SchemaIssue(path, "provenance contains unsupported properties")
                )
            for key in allowed - {"type"}:
                if key in node and not isinstance(node[key], bool):
                    issues.append(
                        SchemaIssue(f"{path}.{key}", "provenance flags must be boolean")
                    )

    walk(ui_dsl, "$.ui_dsl", 0)
    return tuple(issues)
