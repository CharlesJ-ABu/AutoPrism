from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.evidence import sha256_bytes
from app.models.evidence import (
    CalculationRun,
    EvidenceArtifact,
    EvidenceFragment,
    MetricObservation,
    ReviewCase,
    ReviewDecision,
    TrustAssessment,
    TrustState,
    ValidationRun,
    VerificationState,
)
from app.services.artifact_store import LocalArtifactStore


TRUST_POLICY_VERSION = "trust-eligibility-v1"


class TrustService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        artifact_store: LocalArtifactStore | None = None,
    ):
        self.db = db
        self.artifact_store = artifact_store or LocalArtifactStore(
            Path(settings.ARTIFACT_STORAGE_PATH)
        )

    async def assess(
        self,
        *,
        observation_id: uuid.UUID,
        validation_run_id: uuid.UUID | None,
    ) -> TrustAssessment:
        observation = await self.db.get(MetricObservation, observation_id)
        if observation is None:
            raise LookupError("observation not found")
        validation = (
            await self.db.get(ValidationRun, validation_run_id)
            if validation_run_id
            else None
        )
        if validation_run_id and validation is None:
            raise LookupError("validation run not found")
        if validation and str(observation.id) not in validation.observation_ids:
            raise ValueError("validation run does not include the observation")

        replacement = (
            await self.db.execute(
                select(MetricObservation)
                .where(MetricObservation.supersedes_id == observation.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        fragment = await self.db.get(EvidenceFragment, observation.evidence_fragment_id)
        artifact = None
        artifact_integrity = False
        text_integrity = False
        if fragment is not None:
            from app.models.evidence import SourceSnapshot

            snapshot = await self.db.get(SourceSnapshot, fragment.snapshot_id)
            if snapshot is not None:
                artifact = await self.db.get(EvidenceArtifact, snapshot.artifact_id)
        if artifact is not None:
            try:
                content = self.artifact_store.read(artifact.sha256)
                artifact_integrity = (
                    len(content) == artifact.byte_size
                    and sha256_bytes(content) == artifact.sha256
                )
            except (FileNotFoundError, ValueError):
                artifact_integrity = False
        if fragment is not None and fragment.extracted_text is not None:
            text_integrity = (
                fragment.extracted_text_sha256 is not None
                and sha256_bytes(fragment.extracted_text.encode("utf-8"))
                == fragment.extracted_text_sha256
            )

        calculation = (
            await self.db.execute(
                select(CalculationRun)
                .where(CalculationRun.output_observation_id == observation.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        calculation_required = (
            observation.raw_value.get("origin") == "deterministic_calculation"
        )
        independent_sources = (
            int(validation.result.get("independent_source_count", 0))
            if validation
            else 0
        )
        review_decision = None
        if validation:
            review_case = (
                await self.db.execute(
                    select(ReviewCase)
                    .where(ReviewCase.validation_run_id == validation.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if review_case:
                review_decision = (
                    await self.db.execute(
                        select(ReviewDecision)
                        .where(ReviewDecision.review_case_id == review_case.id)
                        .order_by(desc(ReviewDecision.created_at), desc(ReviewDecision.id))
                        .limit(1)
                    )
                ).scalar_one_or_none()

        reasons: list[str] = []
        if replacement is not None:
            reasons.append("OBSERVATION_SUPERSEDED")
        if observation.trust_state in {
            TrustState.REJECTED,
            TrustState.LEGACY_UNVERIFIED,
        }:
            reasons.append("OBSERVATION_STATE_INELIGIBLE")
        if not artifact_integrity:
            reasons.append("ARTIFACT_INTEGRITY_NOT_PROVEN")
        if not text_integrity:
            reasons.append("FRAGMENT_INTEGRITY_NOT_PROVEN")
        if validation is None:
            reasons.append("PASSED_VALIDATION_REQUIRED")
        elif validation.state is not VerificationState.PASSED:
            reasons.append("VALIDATION_NOT_PASSED")
        if validation is not None and independent_sources < 2:
            reasons.append("INSUFFICIENT_INDEPENDENT_SOURCES")
        if calculation_required and calculation is None:
            reasons.append("CALCULATION_RUN_REQUIRED")

        assessment = TrustAssessment(
            observation_id=observation.id,
            validation_run_id=validation.id if validation else None,
            calculation_run_id=calculation.id if calculation else None,
            review_decision_id=review_decision.id if review_decision else None,
            eligible=not reasons,
            reason_codes=reasons or ["ELIGIBLE_UNDER_POLICY"],
            policy_version=TRUST_POLICY_VERSION,
            details={
                "current_revision_head": replacement is None,
                "artifact_integrity": artifact_integrity,
                "fragment_integrity": text_integrity,
                "validation_state": validation.state.value if validation else None,
                "independent_source_count": independent_sources,
                "calculation_replay_recorded": (
                    calculation is not None if calculation_required else None
                ),
                "human_review_outcome": (
                    review_decision.outcome.value if review_decision else None
                ),
                "stored_trust_state": observation.trust_state.value,
            },
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment
