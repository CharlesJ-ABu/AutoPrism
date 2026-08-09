import unittest
from decimal import getcontext

from app.domain.numeric import (
    NUMERIC_ENGINE_VERSION,
    calculate_interval,
    canonical_decimal,
    convert_currency,
    convert_unit,
    make_interval,
    unit_registry_payload,
)


class NumericDomainTests(unittest.TestCase):
    def test_process_decimal_context_cannot_change_results(self):
        previous_precision = getcontext().prec
        try:
            getcontext().prec = 4
            value = make_interval(1, uncertainty_kind="exact", absolute_error=None)
            result, _ = convert_unit(
                value,
                from_unit="mile",
                to_unit="meter",
                output_quantum="0.000001",
            )
            self.assertEqual(canonical_decimal(result.value), "1609.344")
        finally:
            getcontext().prec = previous_precision

    def test_registry_rejects_semantic_count_aliases(self):
        value = make_interval(1, uncertainty_kind="exact", absolute_error=None)
        with self.assertRaisesRegex(ValueError, "semantic"):
            convert_unit(
                value,
                from_unit="record",
                to_unit="vehicle",
                output_quantum="1",
            )
        payload = unit_registry_payload()
        self.assertEqual(payload["version"], "unit-registry-v1")
        self.assertTrue(any(item["code"] == "kilometer" for item in payload["units"]))

    def test_unit_conversion_propagates_bounds_and_rounding(self):
        value = make_interval(
            "1.25",
            uncertainty_kind="bounded",
            absolute_error="0.01",
        )
        result, plan = convert_unit(
            value,
            from_unit="kilometer",
            to_unit="meter",
            output_quantum="1",
        )
        self.assertEqual(canonical_decimal(result.value), "1250")
        self.assertEqual(canonical_decimal(result.absolute_error), "10")
        self.assertEqual(plan["factor"], "1000")

    def test_currency_conversion_requires_exact_pair_and_propagates_rate_error(self):
        amount = make_interval(
            "100",
            uncertainty_kind="bounded",
            absolute_error="1",
        )
        rate = make_interval(
            "7.2",
            uncertainty_kind="bounded",
            absolute_error="0.02",
        )
        result, plan = convert_currency(
            amount,
            rate,
            from_currency="USD",
            to_currency="CNY",
            rate_base_currency="USD",
            rate_quote_currency="CNY",
            output_quantum="0.01",
        )
        self.assertEqual(canonical_decimal(result.value), "720")
        self.assertEqual(canonical_decimal(result.absolute_error), "9.22")
        self.assertEqual(plan["direction"], "direct")
        with self.assertRaisesRegex(ValueError, "pair"):
            convert_currency(
                amount,
                rate,
                from_currency="EUR",
                to_currency="CNY",
                rate_base_currency="USD",
                rate_quote_currency="CNY",
                output_quantum="0.01",
            )

    def test_unknown_uncertainty_never_becomes_zero(self):
        with self.assertRaisesRegex(ValueError, "unknown uncertainty"):
            make_interval(1, uncertainty_kind="unknown", absolute_error=None)

    def test_bounded_calculation_uses_half_even_and_interval_arithmetic(self):
        inputs = [
            make_interval("10", uncertainty_kind="bounded", absolute_error="0.2"),
            make_interval("20", uncertainty_kind="bounded", absolute_error="0.3"),
        ]
        result, plan = calculate_interval(
            "add",
            inputs,
            parameters={},
            output_quantum="1",
        )
        self.assertEqual(canonical_decimal(result.value), "30")
        self.assertEqual(canonical_decimal(result.absolute_error), "0.5")
        self.assertEqual(plan["engine_version"], NUMERIC_ENGINE_VERSION)

    def test_division_fails_if_denominator_uncertainty_contains_zero(self):
        with self.assertRaisesRegex(ValueError, "contains zero"):
            calculate_interval(
                "divide",
                [
                    make_interval(1, uncertainty_kind="exact", absolute_error=None),
                    make_interval(
                        "0.1",
                        uncertainty_kind="bounded",
                        absolute_error="0.2",
                    ),
                ],
                parameters={"unit_plan": {"result": "ratio"}},
                output_quantum="0.01",
            )


if __name__ == "__main__":
    unittest.main()
