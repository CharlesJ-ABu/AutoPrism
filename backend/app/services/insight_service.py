from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import sha256_json
from app.models.evidence import (
    L2Insight,
    L2InsightInput,
    MetricObservation,
    TrustAssessment,
)


L2_ENGINE_VERSION = "deterministic-stored-summary-v1"
L2_PROMPT_VERSION = "stored-input-contract-v1"


class InsightService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, observation_ids: list[uuid.UUID], *, created_by: str) -> L2Insight:
        if len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observation_ids must not contain duplicates")
        observations: list[MetricObservation] = []
        assessments: list[TrustAssessment] = []
        for observation_id in observation_ids:
            observation = await self.db.get(MetricObservation, observation_id)
            if observation is None:
                raise LookupError(f"observation not found: {observation_id}")
            replacement = (
                await self.db.execute(
                    select(MetricObservation)
                    .where(MetricObservation.supersedes_id == observation.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if replacement is not None:
                raise ValueError(f"observation is superseded: {observation.id}")
            assessment = (
                await self.db.execute(
                    select(TrustAssessment)
                    .where(TrustAssessment.observation_id == observation.id)
                    .order_by(desc(TrustAssessment.created_at), desc(TrustAssessment.id))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if assessment is None or not assessment.eligible:
                raise ValueError(
                    f"observation lacks a current eligible trust assessment: {observation.id}"
                )
            observations.append(observation)
            assessments.append(assessment)

        input_snapshot = [
            {
                "observation_id": str(observation.id),
                "assessment_id": str(assessment.id),
                "metric_key": observation.metric_key,
                "normalized_value": observation.normalized_value,
                "unit": observation.unit,
                "currency": observation.currency,
                "period_start": observation.period_start,
                "period_end": observation.period_end,
                "geographic_scope": observation.geographic_scope,
                "dimensions": observation.dimensions,
            }
            for observation, assessment in zip(observations, assessments)
        ]
        input_hash = sha256_json(
            {
                "engine_version": L2_ENGINE_VERSION,
                "prompt_version": L2_PROMPT_VERSION,
                "inputs": input_snapshot,
            }
        )
        existing = (
            await self.db.execute(
                select(L2Insight).where(L2Insight.input_hash == input_hash)
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing

        title = f"可信输入摘要 · {len(observations)} 项指标"
        output = {
            "summary": (
                f"本摘要仅使用 {len(observations)} 条已通过 "
                "trust-eligibility-v1 的数据库观测；未浏览、补值或执行模型数学。"
            ),
            "items": input_snapshot,
            "limitations": [
                "这是确定性证据摘要，不是外部事实补充或预测。",
                "任何输入被修订后，本历史摘要保留但不再代表当前资格集合。",
            ],
        }
        insight = L2Insight(
            title=title,
            input_hash=input_hash,
            engine_version=L2_ENGINE_VERSION,
            prompt_version=L2_PROMPT_VERSION,
            output=output,
            created_by=created_by,
        )
        self.db.add(insight)
        await self.db.flush()
        for ordinal, (observation, assessment) in enumerate(
            zip(observations, assessments)
        ):
            self.db.add(
                L2InsightInput(
                    insight_id=insight.id,
                    ordinal=ordinal,
                    observation_id=observation.id,
                    trust_assessment_id=assessment.id,
                )
            )
        await self.db.commit()
        await self.db.refresh(insight)
        return insight
