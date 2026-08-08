import unittest

from app.domain.panel_schema import (
    validate_panel_payload,
    validate_panel_schema,
    validate_ui_dsl,
)


VALID_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "brand": {"type": "string"},
        "sales": {"type": "integer", "x-unit": "vehicle"},
        "share": {"type": "number", "x-unit": "percent"},
    },
    "required": ["brand", "sales"],
    "x-autoprism": {
        "time_dimension": "month",
        "geographic_dimension": "market",
        "aggregation": {"sales": "sum", "share": "latest"},
        "visualization_mapping": {
            "category": "brand",
            "value": "sales",
            "series": "market",
        },
    },
}


class PanelSchemaTests(unittest.TestCase):
    def test_contract_requires_semantics_beyond_json_types(self):
        self.assertEqual(validate_panel_schema(VALID_SCHEMA), ())
        broken = {**VALID_SCHEMA, "x-autoprism": {}}
        self.assertGreaterEqual(len(validate_panel_schema(broken)), 4)

    def test_payload_is_validated_by_frozen_schema(self):
        self.assertEqual(
            validate_panel_payload(
                VALID_SCHEMA,
                {"brand": "BYD", "sales": 42, "share": 12.5},
            ),
            (),
        )
        issues = validate_panel_payload(
            VALID_SCHEMA,
            {"brand": "BYD", "sales": "not-a-number"},
        )
        self.assertEqual(len(issues), 1)

    def test_boolean_schema_fails_closed_without_crashing(self):
        issues = validate_panel_payload(False, {})
        self.assertEqual(len(issues), 1)
        self.assertIn("schema must be an object", issues[0].message)

    def test_non_finite_payload_numbers_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                issues = validate_panel_payload(
                    VALID_SCHEMA,
                    {"brand": "BYD", "sales": 42, "share": value},
                )
                self.assertTrue(
                    any("must be finite" in issue.message for issue in issues)
                )

    def test_safe_ui_dsl_is_bound_to_schema_fields(self):
        schema = {
            **VALID_SCHEMA,
            "properties": {
                **VALID_SCHEMA["properties"],
                "records": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
            },
        }
        dsl = {
            "type": "stack",
            "children": [
                {"type": "metric", "field": "sales", "label": "Sales"},
                {"type": "table", "field": "records", "columns": ["name"]},
                {"type": "provenance", "show_source": True},
            ],
        }
        self.assertEqual(validate_ui_dsl(schema, dsl), ())
        issues = validate_ui_dsl(
            schema,
            {"type": "chart", "field": "sales"},
        )
        self.assertIn("unsupported UI DSL type", issues[0].message)
        self.assertTrue(
            validate_ui_dsl(
                schema,
                {"type": "table", "field": "sales", "columns": ["unknown"]},
            )
        )


if __name__ == "__main__":
    unittest.main()
