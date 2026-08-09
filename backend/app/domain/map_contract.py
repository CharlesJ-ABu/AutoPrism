"""Deterministic contracts for evidence-bound insight map features."""

from __future__ import annotations

from collections.abc import Mapping
import math
from decimal import Decimal
from typing import Any

from app.domain.evidence import sha256_json
from app.domain.panel_schema import GEO_SCOPE_CONTRACT_VERSION, MAP_DISPLAY_TYPES


TRUSTED_MAP_CONTRACT_VERSION = "trusted-insight-map-v1"


def _valid_position(value: Any) -> bool:
    if not isinstance(value, list) or len(value) != 2:
        return False
    longitude, latitude = value
    if any(
        isinstance(item, bool) or not isinstance(item, (int, float, Decimal))
        for item in value
    ):
        return False
    return bool(
        math.isfinite(float(longitude))
        and math.isfinite(float(latitude))
        and -180 <= longitude <= 180
        and -90 <= latitude <= 90
    )


def is_supported_geographic_scope(scope: Any) -> bool:
    if not isinstance(scope, Mapping):
        return False
    if scope.get("contract_version") != GEO_SCOPE_CONTRACT_VERSION:
        return False
    if scope.get("display_type") not in MAP_DISPLAY_TYPES:
        return False
    if not isinstance(scope.get("label"), str) or not scope["label"].strip():
        return False
    if not isinstance(scope.get("source_fields"), Mapping) or not scope["source_fields"]:
        return False
    geometry = scope.get("geometry")
    if not isinstance(geometry, Mapping):
        return False
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        return _valid_position(coordinates)
    if geometry_type == "LineString":
        return bool(
            isinstance(coordinates, list)
            and len(coordinates) == 2
            and all(_valid_position(position) for position in coordinates)
        )
    if geometry_type == "Polygon":
        if not (
            isinstance(coordinates, list)
            and len(coordinates) == 1
            and isinstance(coordinates[0], list)
            and 4 <= len(coordinates[0]) <= 500
            and all(_valid_position(position) for position in coordinates[0])
        ):
            return False
        return coordinates[0][0] == coordinates[0][-1]
    return False


def build_trusted_map_features(
    *,
    input_hash: str,
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group accepted observation geographies into immutable map features."""

    grouped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        scope = entry.get("scope")
        if entry.get("geography_accepted") is not True:
            continue
        if not is_supported_geographic_scope(scope):
            continue
        scope_hash = sha256_json(scope)
        group = grouped.setdefault(
            scope_hash,
            {
                "scope": dict(scope),
                "observation_ids": [],
                "trust_assessment_ids": [],
                "panel_version_keys": set(),
            },
        )
        group["observation_ids"].append(str(entry["observation_id"]))
        group["trust_assessment_ids"].append(str(entry["trust_assessment_id"]))
        group["panel_version_keys"].add(str(entry["panel_version_key"]))

    features: list[dict[str, Any]] = []
    for scope_hash, group in grouped.items():
        scope = group["scope"]
        feature_id = sha256_json(
            {
                "contract_version": TRUSTED_MAP_CONTRACT_VERSION,
                "input_hash": input_hash,
                "scope_hash": scope_hash,
                "observation_ids": group["observation_ids"],
                "trust_assessment_ids": group["trust_assessment_ids"],
            }
        )
        features.append(
            {
                "id": feature_id,
                "contract_version": TRUSTED_MAP_CONTRACT_VERSION,
                "display_type": scope["display_type"],
                "label": scope["label"],
                "geometry": scope["geometry"],
                "observation_ids": group["observation_ids"],
                "trust_assessment_ids": group["trust_assessment_ids"],
                "panel_version_keys": sorted(group["panel_version_keys"]),
            }
        )
    return sorted(features, key=lambda item: item["id"])
