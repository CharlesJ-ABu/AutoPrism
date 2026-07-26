import os
import tempfile
import unittest
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.ai.providers import StructuredModelResponse
from app.acquisition.contracts import FetchRequest, FetchResult
from app.core.database import async_engine, async_session_maker
from app.main import app
from app.models.evidence import EvidenceArtifact, EvidenceFragment, SourceSnapshot
from app.models.dashboards import (
    Dashboard,
    DashboardVersion,
    PanelDefinition,
    PanelVersion,
    TemplateKind,
)
from app.models.evidence import MetricObservation
from app.models.sources import (
    CollectionJob,
    CollectionJobState,
    HumanActionRequest,
    SourceDefinition,
    SourceKind,
    SourcePool,
)
from app.services.artifact_store import LocalArtifactStore
from app.services.collection_service import CollectionService
from app.services.extraction_service import ExtractionService
from app.services.trust_service import TrustService
from app.services.verification_service import VerificationService


class FakeFetcher:
    def __init__(self, content: bytes):
        self.content = content

    async def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            requested_url=request.url,
            final_url=request.url,
            status_code=200,
            headers={"content-type": "text/html"},
            content=self.content,
            retrieved_at=datetime(2026, 7, 25, 0, 0, 0),
            media_type="text/html",
        )


class FakeProvider:
    def __init__(self, data):
        self.data = data

    async def generate(self, **kwargs):
        return StructuredModelResponse(
            data=self.data,
            provider="fake",
            model="deterministic-test",
            raw_metadata={},
        )


@unittest.skipUnless(
    os.getenv("AUTOPRISM_RUN_DB_TESTS") == "1",
    "set AUTOPRISM_RUN_DB_TESTS=1 against the disposable test database",
)
class CollectionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        # IsolatedAsyncioTestCase creates a fresh loop per test. Dispose pooled
        # asyncpg connections before that loop closes.
        await async_engine.dispose()

    async def test_collection_persists_artifact_snapshot_and_fragments(self):
        suffix = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary_directory:
            async with async_session_maker() as db:
                pool = SourcePool(
                    key=f"integration-{suffix}",
                    name="Integration",
                    topic="Automotive",
                )
                db.add(pool)
                await db.flush()
                source = SourceDefinition(
                    pool_id=pool.id,
                    key="official-html",
                    name="Official HTML",
                    canonical_url="https://example.test/report",
                    kind=SourceKind.HTML,
                    global_reputation=1,
                    topic_authority=1,
                )
                db.add(source)
                await db.flush()
                job = CollectionJob(
                    source_definition_id=source.id,
                    idempotency_key=f"integration:{suffix}",
                )
                db.add(job)
                await db.commit()

                result = await CollectionService(
                    db,
                    fetcher=FakeFetcher(
                        b"<html><head><title>Official</title></head>"
                        b"<body><h1 id='metric'>Sales</h1><p>42 vehicles</p></body></html>"
                    ),
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).run_job(job.id)

                self.assertEqual(result.state, CollectionJobState.SUCCEEDED)
                self.assertIsNotNone(result.result_snapshot_id)
                snapshot = await db.get(SourceSnapshot, result.result_snapshot_id)
                artifact = await db.get(EvidenceArtifact, snapshot.artifact_id)
                self.assertEqual(
                    LocalArtifactStore(Path(temporary_directory)).read(artifact.sha256),
                    (
                        b"<html><head><title>Official</title></head>"
                        b"<body><h1 id='metric'>Sales</h1><p>42 vehicles</p></body></html>"
                    ),
                )
                count = await db.scalar(
                    select(func.count(EvidenceFragment.id)).where(
                        EvidenceFragment.snapshot_id == snapshot.id
                    )
                )
                self.assertEqual(count, 2)

    async def test_database_rejects_immutable_artifact_update(self):
        async with async_session_maker() as db:
            artifact = EvidenceArtifact(
                sha256=uuid.uuid4().hex * 2,
                byte_size=1,
                media_type="text/plain",
                storage_uri="file:///tmp/immutable-test",
            )
            db.add(artifact)
            await db.commit()
            with self.assertRaises(DBAPIError):
                await db.execute(
                    text(
                        "UPDATE evidence_artifacts "
                        "SET media_type = 'application/json' "
                        "WHERE id = :artifact_id"
                    ),
                    {"artifact_id": artifact.id},
                )
                await db.commit()
            await db.rollback()

    async def test_missing_user_credentials_creates_human_action(self):
        suffix = uuid.uuid4().hex
        async with async_session_maker() as db:
            pool = SourcePool(
                key=f"blocked-{suffix}",
                name="Blocked",
                topic="Automotive",
            )
            db.add(pool)
            await db.flush()
            source = SourceDefinition(
                pool_id=pool.id,
                key="login-source",
                name="Login Source",
                canonical_url="https://example.test/private",
                kind=SourceKind.HTML,
                requires_auth=True,
                global_reputation=0.5,
                topic_authority=0.5,
            )
            db.add(source)
            await db.flush()
            job = CollectionJob(
                source_definition_id=source.id,
                idempotency_key=f"blocked:{suffix}",
            )
            db.add(job)
            await db.commit()
            result = await CollectionService(
                db,
                fetcher=FakeFetcher(b"unused"),
            ).run_job(job.id)
            self.assertEqual(result.state, CollectionJobState.BLOCKED)
            action_count = await db.scalar(
                select(func.count(HumanActionRequest.id)).where(
                    HumanActionRequest.collection_job_id == job.id
                )
            )
            self.assertEqual(action_count, 1)

    async def test_schema_bound_extraction_creates_cited_metric(self):
        suffix = uuid.uuid4().hex
        with tempfile.TemporaryDirectory() as temporary_directory:
            async with async_session_maker() as db:
                pool = SourcePool(
                    key=f"extract-{suffix}",
                    name="Extraction",
                    topic="Automotive",
                )
                dashboard = Dashboard(
                    key=f"dashboard-{suffix}",
                    title="Automotive",
                )
                db.add_all([pool, dashboard])
                await db.flush()
                dashboard_version = DashboardVersion(
                    dashboard_id=dashboard.id,
                    version=1,
                    research_brief={"title": "Automotive"},
                )
                panel = PanelDefinition(
                    dashboard_id=dashboard.id,
                    key="sales",
                )
                source = SourceDefinition(
                    pool_id=pool.id,
                    key="official",
                    name="Official",
                    canonical_url="https://example.test/report",
                    kind=SourceKind.HTML,
                    global_reputation=1,
                    topic_authority=1,
                )
                db.add_all([dashboard_version, panel, source])
                await db.flush()
                panel_version = PanelVersion(
                    panel_id=panel.id,
                    dashboard_version_id=dashboard_version.id,
                    version=1,
                    title="Sales",
                    data_schema={
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "properties": {
                            "brand": {"type": "string"},
                            "sales": {"type": "integer", "x-unit": "vehicle"},
                        },
                        "required": ["brand", "sales"],
                        "x-autoprism": {
                            "time_dimension": "month",
                            "geographic_dimension": "market",
                            "aggregation": {"sales": "sum"},
                            "visualization_mapping": {
                                "category": "brand",
                                "value": "sales",
                            },
                        },
                    },
                    template_kind=TemplateKind.UI_DSL,
                    ui_dsl={"type": "bar"},
                    visualization_contract={"type": "bar"},
                    extraction_prompt="Extract reported sales.",
                    source_pool_id=pool.id,
                )
                db.add(panel_version)
                await db.flush()
                job = CollectionJob(
                    source_definition_id=source.id,
                    idempotency_key=f"extract:{suffix}",
                )
                db.add(job)
                await db.commit()
                collected = await CollectionService(
                    db,
                    fetcher=FakeFetcher(
                        b"<html><body><p id='sales'>BYD sold 42 vehicles</p></body></html>"
                    ),
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).run_job(job.id)
                fragment = (
                    await db.execute(
                        select(EvidenceFragment).where(
                            EvidenceFragment.snapshot_id
                            == collected.result_snapshot_id
                        )
                    )
                ).scalar_one()
                original_snapshot = await db.get(
                    SourceSnapshot,
                    collected.result_snapshot_id,
                )
                extracted = await ExtractionService(
                    db,
                    FakeProvider(
                        {
                            "records": [
                                {
                                    "data": {"brand": "BYD", "sales": 42},
                                    "evidence": {
                                        "brand": str(fragment.id),
                                        "sales": str(fragment.id),
                                    },
                                }
                            ]
                        }
                    ),
                ).extract(
                    panel_version_id=panel_version.id,
                    snapshot_id=collected.result_snapshot_id,
                )
                self.assertEqual(extracted.issues, ())
                self.assertEqual(len(extracted.observation_ids), 1)
                observation = await db.get(
                    MetricObservation,
                    extracted.observation_ids[0],
                )
                self.assertEqual(observation.normalized_value, {"value": 42})
                self.assertEqual(observation.unit, "vehicle")
                independent_source = SourceDefinition(
                    pool_id=pool.id,
                    key=f"independent-{suffix}",
                    name="Independent official source",
                    canonical_url="https://independent.example.test/report",
                    kind=SourceKind.HTML,
                    global_reputation=1,
                    topic_authority=1,
                )
                db.add(independent_source)
                await db.flush()
                independent_snapshot = SourceSnapshot(
                    source_definition_id=independent_source.id,
                    source_key=independent_source.key,
                    canonical_url=independent_source.canonical_url,
                    artifact_id=original_snapshot.artifact_id,
                    retrieved_at=datetime(2026, 7, 25, 0, 1, 0),
                )
                db.add(independent_snapshot)
                await db.flush()
                independent_fragment = EvidenceFragment(
                    snapshot_id=independent_snapshot.id,
                    locator_type="css_selector",
                    locator={"selector": "#reported-sales"},
                    extracted_text="Independent filing reports 43 vehicles",
                )
                db.add(independent_fragment)
                await db.flush()
                second = MetricObservation(
                    panel_version_key=observation.panel_version_key,
                    schema_version=observation.schema_version,
                    metric_key=observation.metric_key,
                    evidence_fragment_id=independent_fragment.id,
                    raw_value={"value": 43},
                    normalized_value={"value": 43},
                    unit="vehicle",
                    dimensions=observation.dimensions,
                    geographic_scope={},
                )
                same_source = MetricObservation(
                    panel_version_key=observation.panel_version_key,
                    schema_version=observation.schema_version,
                    metric_key=observation.metric_key,
                    evidence_fragment_id=observation.evidence_fragment_id,
                    raw_value={"value": 42},
                    normalized_value={"value": 42},
                    unit="vehicle",
                    dimensions=observation.dimensions,
                    geographic_scope={},
                )
                db.add(second)
                db.add(same_source)
                await db.commit()
                same_source_validation, same_source_review = (
                    await VerificationService(db).validate_observations(
                        [observation.id, same_source.id],
                        absolute_tolerance=0,
                        relative_tolerance=0,
                    )
                )
                self.assertEqual(
                    same_source_validation.state.value,
                    "needs_review",
                )
                self.assertIsNotNone(same_source_review)
                validation, review = await VerificationService(
                    db
                ).validate_observations(
                    [observation.id, second.id],
                    absolute_tolerance=2,
                    relative_tolerance=0,
                )
                self.assertEqual(validation.state.value, "passed")
                self.assertIsNone(review)
                conflict_validation, review_case = await VerificationService(
                    db
                ).validate_observations(
                    [observation.id, second.id],
                    absolute_tolerance=0,
                    relative_tolerance=0,
                )
                self.assertEqual(conflict_validation.state.value, "conflict")
                self.assertIsNotNone(review_case)
                calculated, calculation_run = await VerificationService(db).calculate(
                    operation="add",
                    input_observation_ids=[observation.id, second.id],
                    output_metric_key="combined_sales",
                    output_unit="vehicle",
                )
                self.assertEqual(calculated.normalized_value, {"value": "85"})
                self.assertEqual(calculation_run.engine_version, "decimal-v1")
                trust_assessment = await TrustService(
                    db,
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).assess(
                    observation_id=observation.id,
                    validation_run_id=validation.id,
                )
                self.assertTrue(trust_assessment.eligible)
                same_source_assessment = await TrustService(
                    db,
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).assess(
                    observation_id=same_source.id,
                    validation_run_id=same_source_validation.id,
                )
                self.assertFalse(same_source_assessment.eligible)
                self.assertIn(
                    "VALIDATION_NOT_PASSED",
                    same_source_assessment.reason_codes,
                )

                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    observations_response = await client.get(
                        "/api/v2/evidence/observations",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(observations_response.status_code, 200)
                    self.assertGreaterEqual(len(observations_response.json()), 3)

                    calculations_response = await client.get(
                        "/api/v2/verification/calculations",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(calculations_response.status_code, 200)
                    self.assertEqual(
                        calculations_response.json()[0]["replay_hash"],
                        calculation_run.replay_hash,
                    )

                    validations_response = await client.get(
                        "/api/v2/verification/validations",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(validations_response.status_code, 200)
                    self.assertEqual(len(validations_response.json()), 3)

                    reviews_response = await client.get(
                        "/api/v2/verification/reviews",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(reviews_response.status_code, 200)
                    self.assertEqual(len(reviews_response.json()), 2)
                    selected_review = next(
                        item
                        for item in reviews_response.json()
                        if item["id"] == str(review_case.id)
                    )
                    self.assertEqual(selected_review["decisions"], [])

                    assessments_response = await client.get(
                        "/api/v2/verification/assessments",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(assessments_response.status_code, 200)
                    selected_assessment = next(
                        item
                        for item in assessments_response.json()
                        if item["id"] == str(trust_assessment.id)
                    )
                    self.assertTrue(selected_assessment["currently_eligible"])

                    insight_response = await client.post(
                        "/api/v2/insights",
                        json={
                            "observation_ids": [str(observation.id)],
                            "created_by": "integration-test",
                        },
                    )
                    self.assertEqual(
                        insight_response.status_code,
                        201,
                        insight_response.text,
                    )
                    insight = insight_response.json()
                    self.assertEqual(
                        insight["engine_version"],
                        "deterministic-stored-summary-v1",
                    )
                    self.assertEqual(
                        insight["inputs"][0]["trust_assessment_id"],
                        str(trust_assessment.id),
                    )
                    repeated_insight_response = await client.post(
                        "/api/v2/insights",
                        json={
                            "observation_ids": [str(observation.id)],
                            "created_by": "integration-test",
                        },
                    )
                    self.assertEqual(repeated_insight_response.status_code, 201)
                    self.assertEqual(
                        repeated_insight_response.json()["id"],
                        insight["id"],
                    )

                    first_decision_response = await client.post(
                        f"/api/v2/verification/reviews/{review_case.id}/decisions",
                        json={
                            "outcome": "approved",
                            "decision": {"reason": "Primary filing confirmed."},
                            "decided_by": "integration-reviewer",
                        },
                    )
                    self.assertEqual(first_decision_response.status_code, 201)
                    first_decision = first_decision_response.json()

                    stale_decision_response = await client.post(
                        f"/api/v2/verification/reviews/{review_case.id}/decisions",
                        json={
                            "outcome": "rejected",
                            "decision": {"reason": "Missing superseding link."},
                            "decided_by": "integration-reviewer",
                        },
                    )
                    self.assertEqual(stale_decision_response.status_code, 409)

                    replacement_decision_response = await client.post(
                        f"/api/v2/verification/reviews/{review_case.id}/decisions",
                        json={
                            "outcome": "rejected",
                            "decision": {"reason": "New official correction."},
                            "decided_by": "integration-reviewer",
                            "supersedes_id": first_decision["id"],
                        },
                    )
                    self.assertEqual(replacement_decision_response.status_code, 201)
                    self.assertEqual(
                        replacement_decision_response.json()["supersedes_id"],
                        first_decision["id"],
                    )

                    revision_response = await client.post(
                        f"/api/v2/evidence/observations/{observation.id}/revisions",
                        json={
                            "raw_value": {"value": 44},
                            "normalized_value": {"value": 44},
                            "reason": "Source issued a correction.",
                            "revised_by": "integration-test",
                            "metadata": {"ticket": "TEST-1"},
                        },
                    )
                    self.assertEqual(
                        revision_response.status_code,
                        201,
                        revision_response.text,
                    )
                    revision = revision_response.json()
                    replacement_id = uuid.UUID(
                        revision["replacement_observation_id"]
                    )
                    replacement = await db.get(MetricObservation, replacement_id)
                    self.assertEqual(replacement.supersedes_id, observation.id)
                    self.assertEqual(replacement.normalized_value, {"value": 44})
                    self.assertEqual(replacement.trust_state.value, "unverified")

                    duplicate_response = await client.post(
                        f"/api/v2/evidence/observations/{observation.id}/revisions",
                        json={
                            "raw_value": {"value": 45},
                            "normalized_value": {"value": 45},
                            "reason": "Conflicting second correction.",
                            "revised_by": "integration-test",
                        },
                    )
                    self.assertEqual(duplicate_response.status_code, 409)

                    revisions_response = await client.get(
                        "/api/v2/evidence/revisions",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(revisions_response.status_code, 200)
                    self.assertEqual(len(revisions_response.json()), 1)
                    self.assertEqual(
                        revisions_response.json()[0]["replacement_observation_id"],
                        str(replacement.id),
                    )

                    stale_assessments_response = await client.get(
                        "/api/v2/verification/assessments",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    stale_assessment = next(
                        item
                        for item in stale_assessments_response.json()
                        if item["id"] == str(trust_assessment.id)
                    )
                    self.assertFalse(stale_assessment["currently_eligible"])

                    stale_insight_response = await client.post(
                        "/api/v2/insights",
                        json={
                            "observation_ids": [str(observation.id)],
                            "created_by": "integration-test",
                        },
                    )
                    self.assertEqual(stale_insight_response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
