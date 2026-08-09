from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import (
    CalculationOperation,
    normalize_calculation_contract,
    sha256_json,
    validate_numeric_sources,
)
from app.domain.numeric import (
    CONVERSION_ENGINE_VERSION,
    NUMERIC_ENGINE_VERSION,
    UNIT_REGISTRY_VERSION,
    UncertaintyKind,
    canonical_decimal,
    calculate_interval,
    convert_currency,
    convert_unit,
    decimal_context,
    decimal_value,
    make_interval,
)
from app.models.dashboards import PanelVersion
from app.models.evidence import (
    CalculationRun,
    CalculationRunInput,
    ConversionKind,
    ConversionRun,
    EvidenceArtifact,
    EvidenceFragment,
    MetricObservation,
    ObservationEvidenceLink,
    ObservationEvidenceSet,
    ObservationNumericEvidence,
    ObservationNumericValue,
    ReviewCase,
    SourceSnapshot,
    TrustState,
    TrustAssessment,
    UncertaintyState,
    ValidationRun,
    VerificationState,
)


VALIDATION_RULE_VERSION = "numeric-v3-bounded-source-artifact-publisher"


def observation_numeric_values(
    observations: list[MetricObservation],
) -> list[Any]:
    """Read canonical numeric values without trusting historical JSON shape."""

    values: list[Any] = []
    for observation in observations:
        normalized = observation.normalized_value
        if (
            not isinstance(normalized, dict)
            or "value" not in normalized
            or normalized["value"] is None
        ):
            raise ValueError(
                f"observation {observation.id} lacks a canonical normalized value"
            )
        values.append(normalized["value"])
    return values


def _canonical_scope_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    # Database timestamps use the project's frozen naive-UTC convention. An
    # aware value can still arrive before a flush, so normalize it to that same
    # convention instead of letting equivalent instants hash differently.
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(timespec="microseconds")


def validation_scope_payload(observation: MetricObservation) -> dict[str, Any]:
    """Return the complete immutable comparison scope used by the V2 rule."""

    return {
        "panel_version_key": observation.panel_version_key,
        "schema_version": observation.schema_version,
        "metric_key": observation.metric_key,
        "unit": observation.unit,
        "currency": observation.currency,
        "dimensions": observation.dimensions,
        "geographic_scope": observation.geographic_scope,
        "observed_at": _canonical_scope_datetime(observation.observed_at),
        "period_start": _canonical_scope_datetime(observation.period_start),
        "period_end": _canonical_scope_datetime(observation.period_end),
    }


def validation_comparison_key(observation: MetricObservation) -> str:
    return sha256_json(validation_scope_payload(observation))


def ensure_comparable_observations(
    observations: list[MetricObservation],
) -> None:
    if not observations:
        raise ValueError("at least one observation is required")
    first_scope = validation_scope_payload(observations[0])
    if any(validation_scope_payload(item) != first_scope for item in observations[1:]):
        raise ValueError("observations are not comparable")


def evaluate_validation_rule(
    observations: list[MetricObservation],
    numeric_values: list[ObservationNumericValue],
    *,
    absolute_tolerance: Any,
    relative_tolerance: Any,
    provenance: dict[str, Any],
) -> tuple[VerificationState, dict[str, Any]]:
    """Evaluate the frozen numeric rule from observations and resolved provenance."""

    numeric_result = validate_numeric_sources(
        observation_numeric_values(observations),
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
    )
    if len(numeric_values) != len(observations):
        raise ValueError("every validation input requires frozen numeric uncertainty")
    intervals = [
        make_interval(
            item.value,
            uncertainty_kind=UncertaintyKind(item.uncertainty_kind.value),
            absolute_error=item.absolute_error,
        )
        for item in numeric_values
    ]
    absolute = decimal_value(absolute_tolerance)
    relative = decimal_value(relative_tolerance)
    if absolute < 0 or relative < 0:
        raise ValueError("validation tolerances must not be negative")
    with decimal_context():
        interval_gap = max(
            Decimal("0"),
            max(item.low for item in intervals) - min(item.high for item in intervals),
        )
        scale = max((abs(item.value) for item in intervals), default=Decimal("0"))
        effective_tolerance = max(absolute, scale * relative)
    provenance_issues = provenance["provenance_issues"]
    independent_source_count = provenance["independent_source_count"]
    independent_artifact_count = provenance["independent_artifact_count"]
    independent_publisher_count = provenance["independent_publisher_count"]
    if provenance_issues or min(
        independent_source_count,
        independent_artifact_count,
        independent_publisher_count,
    ) < 2:
        state = VerificationState.NEEDS_REVIEW
    else:
        state = (
            VerificationState.PASSED
            if len(intervals) >= 2 and interval_gap <= effective_tolerance
            else VerificationState.CONFLICT
            if len(intervals) >= 2
            else VerificationState.NEEDS_REVIEW
        )
    result = {
        "minimum": (
            str(numeric_result.minimum)
            if numeric_result.minimum is not None
            else None
        ),
        "maximum": (
            str(numeric_result.maximum)
            if numeric_result.maximum is not None
            else None
        ),
        "spread": (
            str(numeric_result.spread)
            if numeric_result.spread is not None
            else None
        ),
        "relative_spread": (
            str(numeric_result.relative_spread)
            if numeric_result.relative_spread is not None
            else None
        ),
        "independent_source_count": independent_source_count,
        "independent_artifact_count": independent_artifact_count,
        "independent_publisher_count": independent_publisher_count,
        "source_identities": provenance["source_identities"],
        "artifact_identities": provenance["artifact_identities"],
        "publisher_identities": provenance["publisher_identities"],
        "observation_source_identities": provenance[
            "observation_source_identities"
        ],
        "observation_artifact_identities": provenance[
            "observation_artifact_identities"
        ],
        "observation_publisher_identities": provenance[
            "observation_publisher_identities"
        ],
        "provenance_issues": provenance_issues,
        "interval_gap": canonical_decimal(interval_gap),
        "effective_tolerance": canonical_decimal(effective_tolerance),
        "uncertainty_engine_version": "bounded-validation-v1",
        "input_intervals": [
            {
                "observation_id": str(observation.id),
                "value": canonical_decimal(interval.value),
                "absolute_error": canonical_decimal(interval.absolute_error),
                "low": canonical_decimal(interval.low),
                "high": canonical_decimal(interval.high),
            }
            for observation, interval in zip(observations, intervals, strict=True)
        ],
    }
    return state, result


class VerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _evidence_links(
        self,
        observations: list[MetricObservation],
    ) -> dict[uuid.UUID, list[ObservationEvidenceLink]]:
        observation_ids = [item.id for item in observations]
        rows = (
            await self.db.execute(
                select(ObservationEvidenceLink)
                .where(ObservationEvidenceLink.observation_id.in_(observation_ids))
                .order_by(
                    ObservationEvidenceLink.observation_id,
                    ObservationEvidenceLink.ordinal,
                )
            )
        ).scalars().all()
        output: dict[uuid.UUID, list[ObservationEvidenceLink]] = {
            observation_id: [] for observation_id in observation_ids
        }
        for row in rows:
            output[row.observation_id].append(row)
        return output

    async def _load_observations(
        self,
        observation_ids: list[uuid.UUID],
    ) -> list[MetricObservation]:
        if not observation_ids:
            raise ValueError("at least one observation is required")
        if len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observation_ids must not contain duplicates")
        observations = [
            await self.db.get(MetricObservation, observation_id)
            for observation_id in observation_ids
        ]
        if any(item is None for item in observations):
            raise LookupError("one or more observations do not exist")
        return observations

    async def _load_numeric_values(
        self,
        observations: list[MetricObservation],
    ) -> list[ObservationNumericValue]:
        rows = [
            await self.db.get(ObservationNumericValue, item.id)
            for item in observations
        ]
        if any(item is None for item in rows):
            raise ValueError(
                "every observation requires a frozen numeric uncertainty record"
            )
        return rows

    async def resolve_validation_provenance(
        self,
        observations: list[MetricObservation],
    ) -> dict[str, Any]:
        """Resolve source, artifact and publisher identity without inference.

        Evidence links are claim-level. The same physical fragment may support
        several claims, so fragment identity is deliberately de-duplicated
        before resolving its snapshot and artifact.
        """

        links_by_observation = await self._evidence_links(observations)
        observation_ids = [item.id for item in observations]
        evidence_sets = (
            await self.db.execute(
                select(ObservationEvidenceSet).where(
                    ObservationEvidenceSet.observation_id.in_(observation_ids)
                )
            )
        ).scalars().all()
        evidence_set_by_observation = {
            item.observation_id: item for item in evidence_sets
        }
        fragment_ids = {
            link.evidence_fragment_id
            for links in links_by_observation.values()
            for link in links
        }
        fragment_rows = (
            await self.db.execute(
                select(EvidenceFragment, SourceSnapshot, EvidenceArtifact)
                .join(
                    SourceSnapshot,
                    EvidenceFragment.snapshot_id == SourceSnapshot.id,
                )
                .join(
                    EvidenceArtifact,
                    SourceSnapshot.artifact_id == EvidenceArtifact.id,
                )
                .where(EvidenceFragment.id.in_(fragment_ids))
            )
        ).all()
        evidence_by_fragment = {
            fragment.id: (fragment, snapshot, artifact)
            for fragment, snapshot, artifact in fragment_rows
        }
        observation_sources: dict[str, list[str]] = {}
        observation_artifacts: dict[str, list[str]] = {}
        observation_publishers: dict[str, list[str]] = {}
        provenance_issues: list[dict[str, Any]] = []
        resolved_sources: list[str] = []
        resolved_artifacts: list[str] = []
        resolved_publishers: list[str] = []

        for observation in observations:
            observation_key = str(observation.id)
            links = links_by_observation[observation.id]
            evidence_set = evidence_set_by_observation.get(observation.id)
            primary_links = [item for item in links if item.role == "primary"]
            expected_ordinals = list(range(len(links)))
            if not (
                evidence_set is not None
                and evidence_set.citation_count == len(links)
                and bool(links)
                and [item.ordinal for item in links] == expected_ordinals
                and len(primary_links) == 1
                and primary_links[0].ordinal == 0
                and primary_links[0].evidence_fragment_id
                == observation.evidence_fragment_id
            ):
                provenance_issues.append(
                    {
                        "observation_id": observation_key,
                        "reason": "FROZEN_EVIDENCE_SET_INCOMPLETE",
                    }
                )

            unique_fragment_ids = {
                item.evidence_fragment_id for item in links
            }
            resolved_evidence = [
                evidence_by_fragment.get(fragment_id)
                for fragment_id in unique_fragment_ids
            ]
            if (
                not unique_fragment_ids
                or any(item is None for item in resolved_evidence)
            ):
                provenance_issues.append(
                    {
                        "observation_id": observation_key,
                        "reason": "EVIDENCE_FRAGMENT_CONTEXT_MISSING",
                    }
                )
            complete_evidence = [
                item for item in resolved_evidence if item is not None
            ]
            source_ids = {
                snapshot.source_definition_id
                for _, snapshot, _ in complete_evidence
                if snapshot.source_definition_id is not None
            }
            artifacts = {artifact.sha256 for _, _, artifact in complete_evidence}
            if any(
                snapshot.source_definition_id is None
                for _, snapshot, _ in complete_evidence
            ):
                provenance_issues.append(
                    {
                        "observation_id": observation_key,
                        "reason": "SOURCE_DEFINITION_REQUIRED",
                    }
                )

            publishers: set[str] = set()
            missing_publisher_identity = False
            for _, snapshot, _ in complete_evidence:
                source_metadata = (
                    snapshot.source_metadata
                    if isinstance(snapshot.source_metadata, dict)
                    else {}
                )
                publisher = source_metadata.get("publisher_identity")
                if not isinstance(publisher, str) or not publisher.strip():
                    missing_publisher_identity = True
                    continue
                # Publisher identity is a canonical identifier, not a label.
                # Case and surrounding whitespace cannot manufacture
                # independence under this frozen rule.
                publishers.add(publisher.strip().casefold())
            if missing_publisher_identity:
                provenance_issues.append(
                    {
                        "observation_id": observation_key,
                        "reason": "PUBLISHER_IDENTITY_REQUIRED",
                    }
                )

            sources = sorted(str(item) for item in source_ids)
            artifact_identities = sorted(artifacts)
            publisher_identities = sorted(publishers)
            observation_sources[observation_key] = sources
            observation_artifacts[observation_key] = artifact_identities
            observation_publishers[observation_key] = publisher_identities
            if (
                len(sources) != 1
                or len(artifact_identities) != 1
                or len(publisher_identities) != 1
            ):
                provenance_issues.append(
                    {
                        "observation_id": observation_key,
                        "reason": (
                            "OBSERVATION_MUST_RESOLVE_TO_ONE_SOURCE_"
                            "ARTIFACT_PUBLISHER"
                        ),
                        "source_count": len(sources),
                        "artifact_count": len(artifact_identities),
                        "publisher_count": len(publisher_identities),
                    }
                )
                continue
            resolved_sources.append(sources[0])
            resolved_artifacts.append(artifact_identities[0])
            resolved_publishers.append(publisher_identities[0])

        def duplicate_identities(values: list[str]) -> list[str]:
            return sorted({item for item in values if values.count(item) > 1})

        for identity_kind, values in (
            ("SOURCE", resolved_sources),
            ("ARTIFACT", resolved_artifacts),
            ("PUBLISHER", resolved_publishers),
        ):
            duplicates = duplicate_identities(values)
            if duplicates:
                provenance_issues.append(
                    {
                        "reason": (
                            f"CROSS_OBSERVATION_{identity_kind}_NOT_UNIQUE"
                        ),
                        "identities": duplicates,
                    }
                )

        source_identities = sorted(set(resolved_sources))
        artifact_identities = sorted(set(resolved_artifacts))
        publisher_identities = sorted(set(resolved_publishers))
        return {
            "independent_source_count": len(source_identities),
            "independent_artifact_count": len(artifact_identities),
            "independent_publisher_count": len(publisher_identities),
            "source_identities": source_identities,
            "artifact_identities": artifact_identities,
            "publisher_identities": publisher_identities,
            "observation_source_identities": observation_sources,
            "observation_artifact_identities": observation_artifacts,
            "observation_publisher_identities": observation_publishers,
            "provenance_issues": provenance_issues,
        }

    async def replay_validation(self, validation: ValidationRun) -> dict[str, Any]:
        """Recompute a frozen validation without trusting its stored result."""

        if not isinstance(validation.observation_ids, list):
            raise ValueError("validation observation_ids must be an array")
        try:
            observation_ids = [
                uuid.UUID(str(item)) for item in validation.observation_ids
            ]
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("validation contains an invalid observation id") from exc
        observations = await self._load_observations(observation_ids)
        numeric_values = await self._load_numeric_values(observations)
        ensure_comparable_observations(observations)
        if not isinstance(validation.tolerance, dict) or set(
            validation.tolerance
        ) != {"absolute", "relative"}:
            raise ValueError("validation tolerance contract is incomplete")
        provenance = await self.resolve_validation_provenance(observations)
        expected_state, expected_result = evaluate_validation_rule(
            observations,
            numeric_values,
            absolute_tolerance=validation.tolerance["absolute"],
            relative_tolerance=validation.tolerance["relative"],
            provenance=provenance,
        )
        return {
            "observations": observations,
            "expected_comparison_key": validation_comparison_key(observations[0]),
            "expected_state": expected_state,
            "expected_result": expected_result,
            "provenance": provenance,
        }

    async def validate_observations(
        self,
        observation_ids: list[uuid.UUID],
        *,
        absolute_tolerance: Any,
        relative_tolerance: Any,
    ) -> tuple[ValidationRun, ReviewCase | None]:
        observations = await self._load_observations(observation_ids)
        numeric_values = await self._load_numeric_values(observations)
        first = observations[0]
        ensure_comparable_observations(observations)
        provenance = await self.resolve_validation_provenance(observations)
        state, result = evaluate_validation_rule(
            observations,
            numeric_values,
            absolute_tolerance=absolute_tolerance,
            relative_tolerance=relative_tolerance,
            provenance=provenance,
        )
        run = ValidationRun(
            comparison_key=validation_comparison_key(first),
            observation_ids=[str(item.id) for item in observations],
            rule_version=VALIDATION_RULE_VERSION,
            tolerance={
                "absolute": str(absolute_tolerance),
                "relative": str(relative_tolerance),
            },
            result=result,
            state=state,
        )
        self.db.add(run)
        await self.db.flush()
        review = None
        if state in {VerificationState.CONFLICT, VerificationState.NEEDS_REVIEW}:
            reason_codes = []
            if state is VerificationState.CONFLICT:
                reason_codes.append("SOURCE_CONFLICT")
            if provenance["provenance_issues"]:
                reason_codes.append("AMBIGUOUS_OBSERVATION_EVIDENCE_SCOPE")
            if state is VerificationState.NEEDS_REVIEW:
                reason_codes.append("INSUFFICIENT_INDEPENDENT_SOURCES")
            review = ReviewCase(
                validation_run_id=run.id,
                observation_ids=[str(item.id) for item in observations],
                reason_codes=reason_codes,
            )
            self.db.add(review)
            await self.db.flush()
        await self.db.commit()
        return run, review

    async def _current_eligible_assessment(
        self,
        observation_id: uuid.UUID,
    ) -> TrustAssessment:
        assessment = (
            await self.db.execute(
                select(TrustAssessment)
                .where(TrustAssessment.observation_id == observation_id)
                .order_by(TrustAssessment.created_at.desc(), TrustAssessment.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if assessment is None or not assessment.eligible:
            raise ValueError("conversion inputs require a current eligible assessment")
        # Import lazily because TrustService reuses this service for validation
        # replay. This is an execution dependency, not a module-level cycle.
        from app.services.trust_service import TrustService

        if not await TrustService(self.db).is_assessment_current(assessment):
            raise ValueError("conversion input assessment is no longer current")
        return assessment

    async def _numeric_interval(
        self,
        observation: MetricObservation,
    ):
        numeric = await self.db.get(ObservationNumericValue, observation.id)
        if numeric is None:
            raise ValueError("observation has no frozen numeric uncertainty record")
        return numeric, make_interval(
            numeric.value,
            uncertainty_kind=UncertaintyKind(numeric.uncertainty_kind.value),
            absolute_error=numeric.absolute_error,
        )

    async def convert(
        self,
        *,
        input_observation_id: uuid.UUID,
        kind: ConversionKind | str,
        output_metric_key: str,
        output_quantum: Any,
        to_unit: str | None = None,
        to_currency: str | None = None,
        fx_rate_observation_id: uuid.UUID | None = None,
    ) -> tuple[MetricObservation, ConversionRun]:
        conversion_kind = ConversionKind(kind)
        observation = await self.db.get(MetricObservation, input_observation_id)
        if observation is None:
            raise LookupError("input observation does not exist")
        input_assessment = await self._current_eligible_assessment(observation.id)
        input_numeric, input_interval = await self._numeric_interval(observation)

        fx_observation = None
        fx_assessment = None
        fx_numeric = None
        if conversion_kind is ConversionKind.UNIT:
            if not to_unit or to_currency is not None or fx_rate_observation_id is not None:
                raise ValueError("unit conversion requires only to_unit")
            if not observation.unit:
                raise ValueError("input observation has no unit")
            result, plan = convert_unit(
                input_interval,
                from_unit=observation.unit,
                to_unit=to_unit,
                output_quantum=output_quantum,
            )
            output_unit = to_unit
            output_currency = observation.currency
        else:
            if not to_currency or to_unit is not None or fx_rate_observation_id is None:
                raise ValueError(
                    "currency conversion requires to_currency and fx_rate_observation_id"
                )
            if not observation.currency:
                raise ValueError("input observation has no currency")
            fx_observation = await self.db.get(
                MetricObservation, fx_rate_observation_id
            )
            if fx_observation is None:
                raise LookupError("FX rate observation does not exist")
            fx_assessment = await self._current_eligible_assessment(fx_observation.id)
            fx_numeric, fx_interval = await self._numeric_interval(fx_observation)
            if fx_observation.unit != "currency_ratio":
                raise ValueError("FX rate observation must use currency_ratio")
            if not isinstance(fx_observation.dimensions, dict):
                raise ValueError("FX rate observation dimensions are invalid")
            base_currency = fx_observation.dimensions.get("base_currency")
            quote_currency = fx_observation.dimensions.get("quote_currency")
            rate_basis = fx_observation.dimensions.get("rate_basis")
            if rate_basis not in {"instant", "period_end", "period_average"}:
                raise ValueError("FX rate requires an explicit supported time basis")
            if rate_basis == "instant" and (
                observation.observed_at is None
                or observation.observed_at != fx_observation.observed_at
            ):
                raise ValueError("instant FX rate timestamp must exactly match the input")
            if rate_basis == "period_end" and (
                observation.period_end is None
                or observation.period_end != fx_observation.period_end
            ):
                raise ValueError("period-end FX date must exactly match the input")
            if rate_basis == "period_average" and (
                observation.period_start is None
                or observation.period_start != fx_observation.period_start
                or observation.period_end != fx_observation.period_end
            ):
                raise ValueError("period-average FX range must exactly match the input")
            result, plan = convert_currency(
                input_interval,
                fx_interval,
                from_currency=observation.currency,
                to_currency=to_currency,
                rate_base_currency=base_currency,
                rate_quote_currency=quote_currency,
                output_quantum=output_quantum,
            )
            plan["rate_basis"] = rate_basis
            output_unit = observation.unit
            output_currency = to_currency

        try:
            panel_id = uuid.UUID(observation.panel_version_key)
        except (TypeError, ValueError) as exc:
            raise ValueError("input observation panel lineage is invalid") from exc
        panel = await self.db.get(PanelVersion, panel_id)
        properties = (
            panel.data_schema.get("properties")
            if panel is not None and isinstance(panel.data_schema, dict)
            else None
        )
        output_definition = (
            properties.get(output_metric_key) if isinstance(properties, dict) else None
        )
        if (
            not isinstance(output_definition, dict)
            or output_definition.get("type") not in {"number", "integer"}
        ):
            raise ValueError("output_metric_key must be a numeric field in the frozen panel")
        expected_unit = output_definition.get("x-unit")
        if expected_unit != output_unit:
            raise ValueError("output unit does not match the frozen panel schema")
        if output_definition.get("x-currency") != output_currency:
            raise ValueError("output currency does not match the frozen panel schema")

        links_by_observation = await self._evidence_links(
            [item for item in (observation, fx_observation) if item is not None]
        )
        evidence_inputs: list[tuple[uuid.UUID, uuid.UUID]] = []
        seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
        for item in (observation, fx_observation):
            if item is None:
                continue
            for link in links_by_observation.get(item.id, []):
                entry = (link.evidence_fragment_id, item.id)
                if entry not in seen:
                    seen.add(entry)
                    evidence_inputs.append(entry)
        if not evidence_inputs:
            raise ValueError("conversion inputs have no frozen evidence")

        output = MetricObservation(
            panel_version_key=observation.panel_version_key,
            schema_version=observation.schema_version,
            metric_key=output_metric_key,
            evidence_fragment_id=evidence_inputs[0][0],
            raw_value={
                "origin": "deterministic_conversion",
                "input_observation_id": str(observation.id),
                "fx_rate_observation_id": (
                    str(fx_observation.id) if fx_observation else None
                ),
            },
            normalized_value={"value": canonical_decimal(result.value)},
            unit=output_unit,
            currency=output_currency,
            observed_at=observation.observed_at,
            period_start=observation.period_start,
            period_end=observation.period_end,
            dimensions=observation.dimensions,
            # geo-scope-v1 currently proves only direct extraction fields.
            # A conversion must not copy that authority without a dedicated
            # derived-geography contract.
            geographic_scope={},
            trust_state=TrustState.UNVERIFIED,
        )
        self.db.add(output)
        await self.db.flush()
        self.db.add(
            ObservationEvidenceSet(
                observation_id=output.id,
                citation_count=len(evidence_inputs),
            )
        )
        output_error = result.absolute_error
        output_kind = (
            UncertaintyState.EXACT if output_error == 0 else UncertaintyState.BOUNDED
        )
        self.db.add(
            ObservationNumericValue(
                observation_id=output.id,
                value=result.value,
                uncertainty_kind=output_kind,
                absolute_error=output_error,
                uncertainty_basis={
                    "kind": "derived_interval",
                    "engine_version": CONVERSION_ENGINE_VERSION,
                },
                evidence_count=len(evidence_inputs) if output_error != 0 else 0,
            )
        )
        await self.db.flush()
        for ordinal, (fragment_id, source_observation_id) in enumerate(evidence_inputs):
            self.db.add(
                ObservationEvidenceLink(
                    observation_id=output.id,
                    ordinal=ordinal,
                    evidence_fragment_id=fragment_id,
                    role="primary" if ordinal == 0 else "calculation_input",
                    claim_key=output_metric_key,
                    field_path=f"input_observation:{source_observation_id}",
                )
            )
            if output_error != 0:
                self.db.add(
                    ObservationNumericEvidence(
                        observation_id=output.id,
                        ordinal=ordinal,
                        evidence_fragment_id=fragment_id,
                        claim_key=output_metric_key,
                        field_path=f"input_observation:{source_observation_id}",
                    )
                )

        input_snapshot = {
            "input": {
                "observation_id": str(observation.id),
                "assessment_id": str(input_assessment.id),
                "value": canonical_decimal(input_numeric.value),
                "absolute_error": (
                    canonical_decimal(input_numeric.absolute_error)
                    if input_numeric.absolute_error is not None
                    else None
                ),
                "uncertainty_kind": input_numeric.uncertainty_kind.value,
                "unit": observation.unit,
                "currency": observation.currency,
            },
            "fx_rate": (
                {
                    "observation_id": str(fx_observation.id),
                    "assessment_id": str(fx_assessment.id),
                    "value": canonical_decimal(fx_numeric.value),
                    "absolute_error": (
                        canonical_decimal(fx_numeric.absolute_error)
                        if fx_numeric.absolute_error is not None
                        else None
                    ),
                    "uncertainty_kind": fx_numeric.uncertainty_kind.value,
                    "unit": fx_observation.unit,
                    "dimensions": fx_observation.dimensions,
                }
                if fx_observation and fx_assessment and fx_numeric
                else None
            ),
        }
        frozen_result = {
            "value": canonical_decimal(result.value),
            "absolute_error": canonical_decimal(result.absolute_error),
            "low": canonical_decimal(result.low),
            "high": canonical_decimal(result.high),
            "quantum": canonical_decimal(result.quantum),
            "unit": output_unit,
            "currency": output_currency,
        }
        replay_payload = {
            "kind": conversion_kind.value,
            "registry_version": UNIT_REGISTRY_VERSION,
            "engine_version": CONVERSION_ENGINE_VERSION,
            "plan": plan,
            "input_snapshot": input_snapshot,
            "result": frozen_result,
        }
        run = ConversionRun(
            output_observation_id=output.id,
            input_observation_id=observation.id,
            input_trust_assessment_id=input_assessment.id,
            kind=conversion_kind,
            fx_rate_observation_id=(fx_observation.id if fx_observation else None),
            fx_rate_trust_assessment_id=(fx_assessment.id if fx_assessment else None),
            registry_version=UNIT_REGISTRY_VERSION,
            engine_version=CONVERSION_ENGINE_VERSION,
            plan=plan,
            input_snapshot=input_snapshot,
            result=frozen_result,
            replay_hash=sha256_json(replay_payload),
        )
        self.db.add(run)
        await self.db.commit()
        return output, run

    async def calculate(
        self,
        *,
        operation: CalculationOperation | str,
        input_observation_ids: list[uuid.UUID],
        output_metric_key: str,
        output_unit: str | None,
        output_quantum: Any,
        parameters: dict[str, Any] | None = None,
    ) -> tuple[MetricObservation, CalculationRun]:
        observations = await self._load_observations(input_observation_ids)
        contract = normalize_calculation_contract(
            operation,
            observation_numeric_values(observations),
            parameters,
        )
        normalized_operation = contract.operation
        normalized_parameters = contract.parameters
        if normalized_operation in {
            CalculationOperation.MULTIPLY,
            CalculationOperation.DIVIDE,
        }:
            raise ValueError(
                "bounded multiply/divide requires a future dimensional algebra contract"
            )
        first = observations[0]
        if any(
            item.panel_version_key != first.panel_version_key
            or item.schema_version != first.schema_version
            or item.currency != first.currency
            or item.dimensions != first.dimensions
            or item.geographic_scope != first.geographic_scope
            or item.observed_at != first.observed_at
            or item.period_start != first.period_start
            or item.period_end != first.period_end
            for item in observations[1:]
        ):
            raise ValueError("calculation inputs do not share one comparison scope")
        units = {item.unit for item in observations}
        same_unit_operations = {
            CalculationOperation.ADD,
            CalculationOperation.SUBTRACT,
            CalculationOperation.PERCENT_CHANGE,
            CalculationOperation.WEIGHTED_AVERAGE,
        }
        if normalized_operation in same_unit_operations and len(units) != 1:
            raise ValueError(
                f"{normalized_operation.value} requires inputs with the same unit"
            )
        if normalized_operation in {
            CalculationOperation.ADD,
            CalculationOperation.SUBTRACT,
            CalculationOperation.WEIGHTED_AVERAGE,
        } and output_unit != first.unit:
            raise ValueError(
                f"{normalized_operation.value} output_unit must match the input unit"
            )
        if (
            normalized_operation is CalculationOperation.PERCENT_CHANGE
            and output_unit != "percent"
        ):
            raise ValueError("percent_change output_unit must be percent")
        output_currency = (
            None
            if normalized_operation is CalculationOperation.PERCENT_CHANGE
            else first.currency
        )
        assessments = [
            await self._current_eligible_assessment(item.id) for item in observations
        ]
        numeric_values = await self._load_numeric_values(observations)
        intervals = [
            make_interval(
                item.value,
                uncertainty_kind=UncertaintyKind(item.uncertainty_kind.value),
                absolute_error=item.absolute_error,
            )
            for item in numeric_values
        ]
        result, calculation_plan = calculate_interval(
            normalized_operation,
            intervals,
            parameters=normalized_parameters,
            output_quantum=output_quantum,
        )
        try:
            panel_id = uuid.UUID(first.panel_version_key)
        except (TypeError, ValueError) as exc:
            raise ValueError("calculation panel lineage is invalid") from exc
        panel = await self.db.get(PanelVersion, panel_id)
        properties = (
            panel.data_schema.get("properties")
            if panel is not None and isinstance(panel.data_schema, dict)
            else None
        )
        output_definition = (
            properties.get(output_metric_key) if isinstance(properties, dict) else None
        )
        if (
            not isinstance(output_definition, dict)
            or output_definition.get("type") not in {"number", "integer"}
            or output_definition.get("x-unit") != output_unit
            or output_definition.get("x-currency") != output_currency
        ):
            raise ValueError("calculation output must match a frozen numeric schema field")
        links_by_observation = await self._evidence_links(observations)
        evidence_inputs: list[tuple[uuid.UUID, uuid.UUID]] = []
        seen_evidence_inputs: set[tuple[uuid.UUID, uuid.UUID]] = set()
        for observation in observations:
            links = links_by_observation[observation.id]
            fragment_ids = (
                [link.evidence_fragment_id for link in links]
                if links
                else [observation.evidence_fragment_id]
            )
            for fragment_id in fragment_ids:
                evidence_input = (fragment_id, observation.id)
                if evidence_input not in seen_evidence_inputs:
                    evidence_inputs.append(evidence_input)
                    seen_evidence_inputs.add(evidence_input)
        if not evidence_inputs:
            raise ValueError("calculation inputs have no evidence fragments")
        output = MetricObservation(
            panel_version_key=first.panel_version_key,
            schema_version=first.schema_version,
            metric_key=output_metric_key,
            evidence_fragment_id=evidence_inputs[0][0],
            raw_value={
                "origin": "deterministic_calculation",
                "operation": normalized_operation.value,
                "input_observation_ids": [
                    str(item.id) for item in observations
                ],
            },
            normalized_value={"value": canonical_decimal(result.value)},
            unit=output_unit,
            currency=output_currency,
            observed_at=first.observed_at,
            period_start=first.period_start,
            period_end=first.period_end,
            dimensions=first.dimensions,
            geographic_scope={},
            trust_state=TrustState.UNVERIFIED,
        )
        self.db.add(output)
        await self.db.flush()
        self.db.add(
            ObservationEvidenceSet(
                observation_id=output.id,
                citation_count=len(evidence_inputs),
            )
        )
        await self.db.flush()
        output_error = result.absolute_error
        self.db.add(
            ObservationNumericValue(
                observation_id=output.id,
                value=result.value,
                uncertainty_kind=(
                    UncertaintyState.EXACT
                    if output_error == 0
                    else UncertaintyState.BOUNDED
                ),
                absolute_error=output_error,
                uncertainty_basis={
                    "kind": "derived_interval",
                    "engine_version": NUMERIC_ENGINE_VERSION,
                },
                evidence_count=len(evidence_inputs) if output_error != 0 else 0,
            )
        )
        await self.db.flush()
        for ordinal, (fragment_id, input_observation_id) in enumerate(
            evidence_inputs
        ):
            self.db.add(
                ObservationEvidenceLink(
                    observation_id=output.id,
                    ordinal=ordinal,
                    evidence_fragment_id=fragment_id,
                    role="primary" if ordinal == 0 else "calculation_input",
                    claim_key=output_metric_key,
                    field_path=f"input_observation:{input_observation_id}",
                )
            )
            if output_error != 0:
                self.db.add(
                    ObservationNumericEvidence(
                        observation_id=output.id,
                        ordinal=ordinal,
                        evidence_fragment_id=fragment_id,
                        claim_key=output_metric_key,
                        field_path=f"input_observation:{input_observation_id}",
                    )
                )
        frozen_inputs = [
            {
                "observation_id": str(observation.id),
                "assessment_id": str(assessment.id),
                "value": canonical_decimal(numeric.value),
                "absolute_error": (
                    canonical_decimal(numeric.absolute_error)
                    if numeric.absolute_error is not None
                    else None
                ),
                "uncertainty_kind": numeric.uncertainty_kind.value,
                "unit": observation.unit,
                "currency": observation.currency,
            }
            for observation, assessment, numeric in zip(
                observations, assessments, numeric_values, strict=True
            )
        ]
        frozen_result = {
            "value": canonical_decimal(result.value),
            "absolute_error": canonical_decimal(result.absolute_error),
            "low": canonical_decimal(result.low),
            "high": canonical_decimal(result.high),
            "quantum": canonical_decimal(result.quantum),
            "unit": output_unit,
            "currency": output_currency,
        }
        stored_parameters = {
            "operation_parameters": calculation_plan["parameters"],
            "output_quantum": canonical_decimal(result.quantum),
        }
        replay_payload = {
            "operation": normalized_operation.value,
            "input_observation_ids": [str(item.id) for item in observations],
            "inputs": frozen_inputs,
            "parameters": stored_parameters,
            "result": frozen_result,
            "engine_version": NUMERIC_ENGINE_VERSION,
        }
        calculation = CalculationRun(
            output_observation_id=output.id,
            operation=normalized_operation.value,
            input_observation_ids=[str(item.id) for item in observations],
            parameters=stored_parameters,
            result=frozen_result,
            engine_version=NUMERIC_ENGINE_VERSION,
            replay_hash=sha256_json(replay_payload),
        )
        self.db.add(calculation)
        await self.db.flush()
        for ordinal, (observation, assessment) in enumerate(
            zip(observations, assessments, strict=True)
        ):
            self.db.add(
                CalculationRunInput(
                    calculation_run_id=calculation.id,
                    ordinal=ordinal,
                    observation_id=observation.id,
                    trust_assessment_id=assessment.id,
                )
            )
        await self.db.commit()
        return output, calculation
