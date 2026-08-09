import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from app.domain.evidence import (
    CalculationOperation,
    canonical_json,
    execute_calculation,
    normalize_calculation_contract,
    sha256_bytes,
    sha256_json,
    validate_locator,
    validate_numeric_sources,
)
from app.services.artifact_store import LocalArtifactStore


class EvidenceDomainTests(unittest.TestCase):
    def test_canonical_json_and_hash_are_stable(self):
        left = {"单位": "台", "value": 42, "dimensions": {"b": 2, "a": 1}}
        right = {"dimensions": {"a": 1, "b": 2}, "value": 42, "单位": "台"}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(sha256_json(left), sha256_json(right))
        self.assertEqual(
            canonical_json({"value": Decimal("0.123456789012345678901")}),
            '{"value":0.123456789012345678901}',
        )

    def test_locator_contracts(self):
        validate_locator("pdf_page", {"page": 1})
        validate_locator("table_cell", {"sheet": "销量", "cell": "B12"})
        validate_locator("text_span", {"start": 0, "end": 4})
        with self.assertRaises(ValueError):
            validate_locator("pdf_page", {"page": 0})
        with self.assertRaises(ValueError):
            validate_locator("table_cell", {"sheet": "销量"})

    def test_deterministic_calculations(self):
        change = execute_calculation("percent_change", [100, 125])
        self.assertEqual(change.value, Decimal("25.00"))
        weighted = execute_calculation(
            CalculationOperation.WEIGHTED_AVERAGE,
            [10, 20],
            weights=[1, 3],
        )
        self.assertEqual(weighted.value, Decimal("17.5"))
        with self.assertRaises(ValueError):
            execute_calculation(
                "divide",
                [1, 0],
                parameters={"unit_plan": {"output": "ratio"}},
            )

    def test_calculation_contract_is_strict_and_canonical(self):
        normalized = normalize_calculation_contract(
            "weighted_average",
            [10, 20],
            {"weights": (1, 3)},
        )
        self.assertEqual(normalized.parameters, {"weights": [1, 3]})
        self.assertEqual(normalized.weights, (Decimal("1"), Decimal("3")))

        with self.assertRaisesRegex(ValueError, "raw_inputs must be an array"):
            execute_calculation("add", "10")
        with self.assertRaisesRegex(ValueError, "parameters must be an object"):
            normalize_calculation_contract("add", [10], [1])
        with self.assertRaisesRegex(ValueError, "unsupported calculation parameters"):
            execute_calculation("add", [10], parameters={"weights": [1]})
        with self.assertRaisesRegex(ValueError, "unsupported calculation parameters"):
            execute_calculation(
                "weighted_average",
                [10, 20],
                parameters={"weights": [1, 3], "unexpected": True},
            )

        for invalid_weights in (
            "1,3",
            [1, "3"],
            [1, True],
            [1, float("nan")],
            [1, float("inf")],
        ):
            with self.subTest(weights=invalid_weights):
                with self.assertRaises(ValueError):
                    execute_calculation(
                        "weighted_average",
                        [10, 20],
                        parameters={"weights": invalid_weights},
                    )
        with self.assertRaisesRegex(ValueError, "one weight per input"):
            execute_calculation(
                "weighted_average",
                [10, 20],
                parameters={"weights": [1]},
            )

        for invalid_unit_plan in (None, "kg*vehicle", {}, []):
            with self.subTest(unit_plan=invalid_unit_plan):
                with self.assertRaisesRegex(ValueError, "unit_plan object"):
                    execute_calculation(
                        "multiply",
                        [2, 3],
                        parameters={"unit_plan": invalid_unit_plan},
                    )
        multiplied = execute_calculation(
            "multiply",
            [2, 3],
            parameters={"unit_plan": {"output": "vehicle-km"}},
        )
        self.assertEqual(multiplied.value, Decimal("6"))

    def test_cross_source_validation(self):
        passed = validate_numeric_sources(
            ["100", "101"],
            absolute_tolerance="2",
            relative_tolerance="0.01",
        )
        self.assertEqual(passed.state, "passed")
        conflict = validate_numeric_sources(
            [100, 120],
            absolute_tolerance=2,
            relative_tolerance="0.01",
        )
        self.assertEqual(conflict.state, "conflict")
        self.assertEqual(
            validate_numeric_sources([100]).state,
            "needs_review",
        )
        with self.assertRaises(ValueError):
            validate_numeric_sources([100, 101], absolute_tolerance="NaN")
        with self.assertRaises(ValueError):
            validate_numeric_sources([100, 101], relative_tolerance="-0.1")

    def test_decimal_overflow_fails_closed(self):
        extreme = "1e999999999999999999"
        with self.assertRaises(ValueError):
            execute_calculation(
                "multiply",
                [extreme, extreme],
                parameters={"unit_plan": {"output": "squared"}},
            )
        with self.assertRaises(ValueError):
            validate_numeric_sources(
                [f"-{extreme}", extreme],
                absolute_tolerance="0",
                relative_tolerance="0",
            )

    def test_local_artifact_store_is_content_addressed_and_verified(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = LocalArtifactStore(Path(temporary_directory))
            content = "可追溯原始公告".encode("utf-8")
            first = store.put(content)
            second = store.put(content)

            self.assertEqual(first, second)
            self.assertEqual(first.sha256, sha256_bytes(content))
            self.assertEqual(store.read(first.sha256), content)
            self.assertEqual(len(list(Path(temporary_directory).rglob(first.sha256))), 1)

            store.path_for(first.sha256).write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                store.read(first.sha256)
            with self.assertRaises(ValueError):
                store.put(content)


if __name__ == "__main__":
    unittest.main()
