import unittest

from app.domain.map_contract import (
    TRUSTED_MAP_CONTRACT_VERSION,
    build_trusted_map_features,
)


class TrustedMapContractTests(unittest.TestCase):
    def test_features_group_only_accepted_identical_scopes(self):
        scope = {
            "contract_version": "geo-scope-v1",
            "display_type": "MARKER",
            "label": "Shenzhen",
            "geometry": {"type": "Point", "coordinates": [114.0579, 22.5431]},
            "source_fields": {
                "label": "location",
                "latitude": "latitude",
                "longitude": "longitude",
            },
        }
        features = build_trusted_map_features(
            input_hash="a" * 64,
            entries=[
                {
                    "observation_id": "observation-1",
                    "trust_assessment_id": "assessment-1",
                    "panel_version_key": "panel-1",
                    "scope": scope,
                    "geography_accepted": True,
                },
                {
                    "observation_id": "observation-2",
                    "trust_assessment_id": "assessment-2",
                    "panel_version_key": "panel-1",
                    "scope": scope,
                    "geography_accepted": True,
                },
                {
                    "observation_id": "untrusted",
                    "trust_assessment_id": "assessment-3",
                    "panel_version_key": "panel-2",
                    "scope": scope,
                    "geography_accepted": False,
                },
            ],
        )
        self.assertEqual(len(features), 1)
        self.assertEqual(
            features[0]["contract_version"], TRUSTED_MAP_CONTRACT_VERSION
        )
        self.assertEqual(
            features[0]["observation_ids"],
            ["observation-1", "observation-2"],
        )
        self.assertEqual(features[0]["panel_version_keys"], ["panel-1"])

    def test_malformed_scope_never_becomes_a_feature(self):
        features = build_trusted_map_features(
            input_hash="b" * 64,
            entries=[
                {
                    "observation_id": "observation-1",
                    "trust_assessment_id": "assessment-1",
                    "panel_version_key": "panel-1",
                    "scope": {
                        "contract_version": "geo-scope-v1",
                        "display_type": "MARKER",
                        "label": "Invented",
                        "geometry": {"type": "Point", "coordinates": [0]},
                        "source_fields": {"label": "location"},
                    },
                    "geography_accepted": True,
                }
            ],
        )
        self.assertEqual(features, [])


if __name__ == "__main__":
    unittest.main()
