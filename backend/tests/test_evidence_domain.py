import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from app.domain.evidence import (
    CalculationOperation,
    canonical_json,
    execute_calculation,
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
            execute_calculation("divide", [1, 0])

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
