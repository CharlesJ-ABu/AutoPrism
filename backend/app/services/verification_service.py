from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import (
    execute_calculation,
    sha256_json,
    validate_numeric_sources,
)
from app.models.evidence import (
    CalculationRun,
    EvidenceFragment,
    MetricObservation,
    ReviewCase,
    SourceSnapshot,
    TrustState,
    ValidationRun,
    VerificationState,
)


class VerificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_observations(
        self,
        observation_ids: list[uuid.UUID],
        *,
        absolute_tolerance: Any,
        relative_tolerance: Any,
    ) -> tuple[ValidationRun, ReviewCase | None]:
        if len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observation_ids must not contain duplicates")
        observations = [
            await self.db.get(MetricObservation, observation_id)
            for observation_id in observation_ids
        ]
        if any(item is None for item in observations):
            raise LookupError("one or more observations do not exist")
        first = observations[0]
        if any(
            item.panel_version_key != first.panel_version_key
            or item.schema_version != first.schema_version
            or item.metric_key != first.metric_key
            or item.unit != first.unit
            or item.currency != first.currency
            or item.dimensions != first.dimensions
            or item.geographic_scope != first.geographic_scope
            or item.observed_at != first.observed_at
            or item.period_start != first.period_start
            or item.period_end != first.period_end
            for item in observations[1:]
        ):
            raise ValueError("observations are not comparable")
        fragments = [
            await self.db.get(EvidenceFragment, item.evidence_fragment_id)
            for item in observations
        ]
        snapshots = [
            await self.db.get(SourceSnapshot, fragment.snapshot_id)
            for fragment in fragments
        ]
        source_identities = [
            (
                str(snapshot.source_definition_id)
                if snapshot.source_definition_id
                else f"source_key:{snapshot.source_key}"
            )
            for snapshot in snapshots
        ]
        if len(set(source_identities)) < 2:
            result = validate_numeric_sources(
                [observations[0].normalized_value["value"]],
                absolute_tolerance=absolute_tolerance,
                relative_tolerance=relative_tolerance,
            )
            state = VerificationState.NEEDS_REVIEW
        else:
            result = validate_numeric_sources(
                [item.normalized_value["value"] for item in observations],
                absolute_tolerance=absolute_tolerance,
                relative_tolerance=relative_tolerance,
            )
            state = {
                "passed": VerificationState.PASSED,
                "conflict": VerificationState.CONFLICT,
                "needs_review": VerificationState.NEEDS_REVIEW,
            }[result.state]
        run = ValidationRun(
            comparison_key=sha256_json(
                {
                    "panel_version_key": first.panel_version_key,
                    "schema_version": first.schema_version,
                    "metric_key": first.metric_key,
                    "unit": first.unit,
                    "currency": first.currency,
                    "dimensions": first.dimensions,
                    "geographic_scope": first.geographic_scope,
                    "observed_at": first.observed_at,
                    "period_start": first.period_start,
                    "period_end": first.period_end,
                }
            ),
            observation_ids=[str(item.id) for item in observations],
            rule_version="numeric-v1",
            tolerance={
                "absolute": str(absolute_tolerance),
                "relative": str(relative_tolerance),
            },
            result={
                "minimum": str(result.minimum) if result.minimum is not None else None,
                "maximum": str(result.maximum) if result.maximum is not None else None,
                "spread": str(result.spread) if result.spread is not None else None,
                "relative_spread": (
                    str(result.relative_spread)
                    if result.relative_spread is not None
                    else None
                ),
                "independent_source_count": len(set(source_identities)),
                "source_identities": source_identities,
            },
            state=state,
        )
        self.db.add(run)
        await self.db.flush()
        review = None
        if state in {VerificationState.CONFLICT, VerificationState.NEEDS_REVIEW}:
            review = ReviewCase(
                validation_run_id=run.id,
                observation_ids=[str(item.id) for item in observations],
                reason_codes=[
                    "SOURCE_CONFLICT"
                    if state is VerificationState.CONFLICT
                    else "INSUFFICIENT_INDEPENDENT_SOURCES"
                ],
            )
            self.db.add(review)
            await self.db.flush()
        await self.db.commit()
        return run, review

    async def calculate(
        self,
        *,
        operation: str,
        input_observation_ids: list[uuid.UUID],
        output_metric_key: str,
        output_unit: str | None,
        parameters: dict[str, Any] | None = None,
    ) -> tuple[MetricObservation, CalculationRun]:
        parameters = parameters or {}
        if len(set(input_observation_ids)) != len(input_observation_ids):
            raise ValueError("input_observation_ids must not contain duplicates")
        observations = [
            await self.db.get(MetricObservation, observation_id)
            for observation_id in input_observation_ids
        ]
        if any(item is None for item in observations):
            raise LookupError("one or more input observations do not exist")
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
        same_unit_operations = {"add", "subtract", "percent_change", "weighted_average"}
        if operation in same_unit_operations and len(units) != 1:
            raise ValueError(f"{operation} requires inputs with the same unit")
        if operation in {"add", "subtract", "weighted_average"} and output_unit != first.unit:
            raise ValueError(f"{operation} output_unit must match the input unit")
        if operation == "percent_change" and output_unit != "percent":
            raise ValueError("percent_change output_unit must be percent")
        if operation in {"multiply", "divide"}:
            if not output_unit:
                raise ValueError(f"{operation} requires an explicit output_unit")
            if not parameters.get("unit_plan"):
                raise ValueError(f"{operation} requires an explicit unit_plan")
        result = execute_calculation(
            operation,
            [item.normalized_value["value"] for item in observations],
            weights=parameters.get("weights"),
        )
        output = MetricObservation(
            panel_version_key=first.panel_version_key,
            schema_version=first.schema_version,
            metric_key=output_metric_key,
            evidence_fragment_id=first.evidence_fragment_id,
            raw_value={
                "origin": "deterministic_calculation",
                "operation": operation,
                "input_observation_ids": [
                    str(item.id) for item in observations
                ],
            },
            normalized_value={"value": str(result.value)},
            unit=output_unit,
            dimensions=first.dimensions,
            geographic_scope=first.geographic_scope,
            trust_state=TrustState.UNVERIFIED,
        )
        self.db.add(output)
        await self.db.flush()
        replay_payload = {
            "operation": operation,
            "input_observation_ids": [str(item.id) for item in observations],
            "input_values": [item.normalized_value for item in observations],
            "parameters": parameters,
            "result": str(result.value),
            "engine_version": "decimal-v1",
        }
        calculation = CalculationRun(
            output_observation_id=output.id,
            operation=operation,
            input_observation_ids=[str(item.id) for item in observations],
            parameters=parameters,
            result={"value": str(result.value), "unit": output_unit},
            engine_version="decimal-v1",
            replay_hash=sha256_json(replay_payload),
        )
        self.db.add(calculation)
        await self.db.commit()
        return output, calculation
