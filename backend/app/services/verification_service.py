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
    MetricObservation,
    ReviewCase,
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
        absolute_tolerance: Any = 0,
        relative_tolerance: Any = 0,
    ) -> tuple[ValidationRun, ReviewCase | None]:
        observations = [
            await self.db.get(MetricObservation, observation_id)
            for observation_id in observation_ids
        ]
        if any(item is None for item in observations):
            raise LookupError("one or more observations do not exist")
        first = observations[0]
        if any(
            item.metric_key != first.metric_key
            or item.unit != first.unit
            or item.dimensions != first.dimensions
            for item in observations[1:]
        ):
            raise ValueError("observations are not comparable")
        values = [item.normalized_value["value"] for item in observations]
        result = validate_numeric_sources(
            values,
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
                    "metric_key": first.metric_key,
                    "unit": first.unit,
                    "dimensions": first.dimensions,
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
                    else "INSUFFICIENT_SOURCES"
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
        observations = [
            await self.db.get(MetricObservation, observation_id)
            for observation_id in input_observation_ids
        ]
        if any(item is None for item in observations):
            raise LookupError("one or more input observations do not exist")
        first = observations[0]
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
            raw_value={"calculation": operation},
            normalized_value={"value": str(result.value)},
            unit=output_unit,
            dimensions=first.dimensions,
            geographic_scope=first.geographic_scope,
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
