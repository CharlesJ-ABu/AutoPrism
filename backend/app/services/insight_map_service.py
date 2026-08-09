"""Fail-closed read model for current, evidence-bound L2 map features."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.map_contract import (
    TRUSTED_MAP_CONTRACT_VERSION,
    build_trusted_map_features,
)
from app.models.evidence import (
    L2Insight,
    L2InsightInput,
    MetricObservation,
    TrustAssessment,
)
from app.services.insight_service import L2_ENGINE_VERSION, L2_PROMPT_VERSION
from app.services.trust_service import TrustService


class InsightMapService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_current_features(
        self,
        *,
        panel_version_keys: set[str] | None = None,
        limit: int = 200,
    ) -> dict:
        insights = (
            await self.db.execute(
                select(L2Insight).order_by(
                    desc(L2Insight.created_at),
                    desc(L2Insight.id),
                )
            )
        ).scalars().all()
        trust_service = TrustService(self.db)
        features: list[dict] = []
        stats = {
            "scanned_insights": 0,
            "current_insights": 0,
            "stale_or_invalid_insights": 0,
            "unsupported_contract_insights": 0,
            "without_geography": 0,
            "replay_mismatch_insights": 0,
        }
        for insight in insights:
            if len(features) >= limit:
                break
            rows = (
                await self.db.execute(
                    select(L2InsightInput)
                    .where(L2InsightInput.insight_id == insight.id)
                    .order_by(L2InsightInput.ordinal)
                )
            ).scalars().all()
            observations: list[MetricObservation] = []
            assessments: list[TrustAssessment] = []
            valid_rows = bool(
                rows and [row.ordinal for row in rows] == list(range(len(rows)))
            )
            for row in rows:
                observation = await self.db.get(MetricObservation, row.observation_id)
                assessment = await self.db.get(TrustAssessment, row.trust_assessment_id)
                if (
                    observation is None
                    or assessment is None
                    or assessment.observation_id != observation.id
                ):
                    valid_rows = False
                    break
                observations.append(observation)
                assessments.append(assessment)
            if panel_version_keys and not any(
                observation.panel_version_key in panel_version_keys
                for observation in observations
            ):
                continue
            stats["scanned_insights"] += 1
            if (
                insight.engine_version != L2_ENGINE_VERSION
                or insight.prompt_version != L2_PROMPT_VERSION
                or not isinstance(insight.output, dict)
                or insight.output.get("map_contract_version")
                != TRUSTED_MAP_CONTRACT_VERSION
                or not isinstance(insight.output.get("map_features"), list)
            ):
                stats["unsupported_contract_insights"] += 1
                continue
            current = valid_rows
            if current:
                for assessment in assessments:
                    if not await trust_service.is_assessment_current(assessment):
                        current = False
                        break
            if not current:
                stats["stale_or_invalid_insights"] += 1
                continue

            geography_entries = []
            for observation, assessment in zip(observations, assessments):
                geography = await trust_service.geography_integrity(observation)
                geography_entries.append(
                    {
                        "observation_id": observation.id,
                        "trust_assessment_id": assessment.id,
                        "panel_version_key": observation.panel_version_key,
                        "scope": geography["scope"],
                        "geography_accepted": geography["accepted"],
                    }
                )
            replayed = build_trusted_map_features(
                input_hash=insight.input_hash,
                entries=geography_entries,
            )
            if replayed != insight.output["map_features"]:
                stats["replay_mismatch_insights"] += 1
                continue
            stats["current_insights"] += 1
            if not replayed:
                stats["without_geography"] += 1
                continue
            summary = insight.output.get("summary")
            for feature in replayed:
                if panel_version_keys and not panel_version_keys.intersection(
                    feature["panel_version_keys"]
                ):
                    continue
                features.append(
                    {
                        **feature,
                        "insight_id": str(insight.id),
                        "title": insight.title,
                        "summary": summary if isinstance(summary, str) else "",
                        "input_hash": insight.input_hash,
                        "engine_version": insight.engine_version,
                        "prompt_version": insight.prompt_version,
                        "created_at": insight.created_at,
                    }
                )
                if len(features) >= limit:
                    break
        return {
            "contract_version": TRUSTED_MAP_CONTRACT_VERSION,
            "features": features,
            "stats": stats,
        }
