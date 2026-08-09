import unittest

from sqlalchemy import event

from app.models.evidence import (
    CalculationRun,
    EvidenceArtifact,
    EvidenceFragment,
    ExtractionRunInput,
    ExtractionRunInputSet,
    L2Insight,
    L2InsightInput,
    LineageBackfillAudit,
    MetricObservation,
    ObservationEvidenceLink,
    ObservationEvidenceSet,
    ObservationExtractionLink,
    ObservationGeography,
    ObservationGeographyEvidence,
    ObservationRevision,
    ReviewCase,
    ReviewDecision,
    SourceSnapshot,
    TrustAssessment,
    ValidationRun,
    _reject_immutable_mutation,
)


class EvidenceModelContractTests(unittest.TestCase):
    def test_all_evidence_entities_have_orm_immutability_guards(self):
        immutable_models = (
            EvidenceArtifact,
            SourceSnapshot,
            EvidenceFragment,
            MetricObservation,
            ObservationEvidenceSet,
            ObservationEvidenceLink,
            ObservationExtractionLink,
            ObservationGeography,
            ObservationGeographyEvidence,
            ExtractionRunInput,
            ExtractionRunInputSet,
            LineageBackfillAudit,
            ObservationRevision,
            CalculationRun,
            ValidationRun,
            ReviewCase,
            ReviewDecision,
            TrustAssessment,
            L2Insight,
            L2InsightInput,
        )
        for model in immutable_models:
            with self.subTest(model=model.__name__):
                self.assertTrue(
                    event.contains(model, "before_update", _reject_immutable_mutation)
                )
                self.assertTrue(
                    event.contains(model, "before_delete", _reject_immutable_mutation)
                )

    def test_corrections_and_decisions_have_supersession_links(self):
        self.assertIn("supersedes_id", MetricObservation.__table__.columns)
        self.assertIn("supersedes_id", ReviewDecision.__table__.columns)
        self.assertIn(
            "replacement_observation_id",
            ObservationRevision.__table__.columns,
        )


if __name__ == "__main__":
    unittest.main()
