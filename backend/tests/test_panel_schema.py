import unittest

from app.domain.panel_schema import validate_panel_payload, validate_panel_schema


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


if __name__ == "__main__":
    unittest.main()
