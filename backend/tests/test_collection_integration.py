import os
import tempfile
import unittest
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.ai.providers import DeterministicMappingProvider, StructuredModelResponse
from app.acquisition.contracts import FetchRequest, FetchResult
from app.core.database import async_engine, async_session_maker
from app.core.config import settings
from app.main import app
from app.domain.evidence import sha256_bytes
from app.models.evidence import (
    EvidenceArtifact,
    EvidenceFragment,
    ObservationEvidenceLink,
    ObservationEvidenceSet,
    ObservationExtractionLink,
    ObservationGeography,
    ObservationGeographyEvidence,
    ObservationNumericValue,
    SourceSnapshot,
    ValidationRun,
    VerificationState,
    UncertaintyState,
    ConversionKind,
)
from app.models.dashboards import (
    Dashboard,
    DashboardVersion,
    ExtractionRun,
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
    def __init__(self, content: bytes, media_type: str = "text/html"):
        self.content = content
        self.media_type = media_type

    async def fetch(self, request: FetchRequest) -> FetchResult:
        return FetchResult(
            requested_url=request.url,
            final_url=request.url,
            status_code=200,
            headers={"content-type": self.media_type},
            content=self.content,
            retrieved_at=datetime(2026, 7, 25, 0, 0, 0),
            media_type=self.media_type,
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
                    request_config={"publisher_identity": "example-official"},
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

    async def test_database_rejects_append_only_truncate(self):
        async with async_session_maker() as db:
            with self.assertRaises(DBAPIError):
                await db.execute(text("TRUNCATE TABLE lineage_backfill_audits"))
                await db.commit()
            await db.rollback()

    async def test_database_rejects_late_evidence_insert(self):
        suffix = uuid.uuid4().hex
        async with async_session_maker() as db:
            artifact = EvidenceArtifact(
                sha256=suffix * 2,
                byte_size=1,
                media_type="text/plain",
                storage_uri=f"file:///tmp/{suffix}",
            )
            db.add(artifact)
            await db.flush()
            snapshot = SourceSnapshot(
                source_key=f"frozen-evidence-{suffix}",
                canonical_url=f"https://example.test/{suffix}",
                artifact_id=artifact.id,
                retrieved_at=datetime(2026, 8, 8, 0, 0, 0),
            )
            db.add(snapshot)
            await db.flush()
            primary = EvidenceFragment(
                snapshot_id=snapshot.id,
                locator_type="text_range",
                locator={"start": 0, "end": 1},
                extracted_text="1",
                extracted_text_sha256=sha256_bytes(b"1"),
            )
            late = EvidenceFragment(
                snapshot_id=snapshot.id,
                locator_type="text_range",
                locator={"start": 2, "end": 3},
                extracted_text="2",
                extracted_text_sha256=sha256_bytes(b"2"),
            )
            db.add_all([primary, late])
            await db.flush()
            observation = MetricObservation(
                panel_version_key=f"manual-{suffix}",
                schema_version="1",
                metric_key="value",
                evidence_fragment_id=primary.id,
                raw_value={"value": 1},
                normalized_value={"value": 1},
                geographic_scope={},
                dimensions={},
            )
            db.add(observation)
            await db.flush()
            db.add(
                ObservationEvidenceSet(
                    observation_id=observation.id,
                    citation_count=1,
                )
            )
            await db.flush()
            db.add(
                ObservationEvidenceLink(
                    observation_id=observation.id,
                    ordinal=0,
                    evidence_fragment_id=primary.id,
                    role="primary",
                    claim_key="value",
                    field_path="$.value",
                )
            )
            await db.commit()

            db.add(
                ObservationEvidenceLink(
                    observation_id=observation.id,
                    ordinal=1,
                    evidence_fragment_id=late.id,
                    role="supporting",
                    claim_key="value",
                    field_path="$.value",
                )
            )
            with self.assertRaises(DBAPIError):
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

    async def test_trusted_insight_map_requires_replayable_geography(self):
        suffix = uuid.uuid4().hex
        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            patch.object(settings, "ARTIFACT_STORAGE_PATH", temporary_directory),
        ):
            async with async_session_maker() as db:
                pool = SourcePool(
                    key=f"map-{suffix}",
                    name="Trusted map",
                    topic="Automotive",
                )
                dashboard = Dashboard(
                    key=f"map-dashboard-{suffix}",
                    title="Trusted map",
                )
                db.add_all([pool, dashboard])
                await db.flush()
                dashboard_version = DashboardVersion(
                    dashboard_id=dashboard.id,
                    version=1,
                    research_brief={"title": "Trusted map"},
                )
                panel = PanelDefinition(
                    dashboard_id=dashboard.id,
                    key="regional-sales",
                )
                db.add_all([dashboard_version, panel])
                await db.flush()
                panel_version = PanelVersion(
                    panel_id=panel.id,
                    dashboard_version_id=dashboard_version.id,
                    version=1,
                    title="Regional sales",
                    data_schema={
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "sales": {
                                "type": "integer",
                                "x-unit": "vehicle",
                                "x-uncertainty": {"kind": "exact"},
                            },
                            "sales_thousands": {
                                "type": "number",
                                "x-unit": "thousand_vehicle",
                                "x-uncertainty": {"kind": "exact"},
                            },
                            "sales_total": {
                                "type": "number",
                                "x-unit": "vehicle",
                                "x-uncertainty": {"kind": "exact"},
                            },
                            "revenue_usd": {
                                "type": "number",
                                "x-unit": "currency_unit",
                                "x-currency": "USD",
                                "x-uncertainty": {"kind": "exact"},
                            },
                            "revenue_cny": {
                                "type": "number",
                                "x-unit": "currency_unit",
                                "x-currency": "CNY",
                                "x-uncertainty": {"kind": "exact"},
                            },
                            "fx_usd_cny": {
                                "type": "number",
                                "x-unit": "currency_ratio",
                                "x-uncertainty": {"kind": "exact"},
                            },
                            "base_currency": {"type": "string"},
                            "quote_currency": {"type": "string"},
                            "rate_basis": {"type": "string"},
                            "reported_at": {"type": "string"},
                            "latitude": {
                                "type": "number",
                                "x-unit": "degree_latitude",
                            },
                            "longitude": {
                                "type": "number",
                                "x-unit": "degree_longitude",
                            },
                            "records": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "reported_at": {
                                            "type": "string",
                                            "format": "date-time",
                                        },
                                        "label": {"type": "string"},
                                        "value": {
                                            "type": "number",
                                            "x-unit": "vehicle",
                                        },
                                    },
                                    "required": [
                                        "reported_at",
                                        "label",
                                        "value",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "location",
                            "sales",
                            "revenue_usd",
                            "fx_usd_cny",
                            "base_currency",
                            "quote_currency",
                            "rate_basis",
                            "reported_at",
                            "latitude",
                            "longitude",
                            "records",
                        ],
                        "x-autoprism": {
                            "time_dimension": {
                                "contract_version": "time-scope-v1",
                                "kind": "instant",
                                "field": "reported_at",
                            },
                            "geographic_dimension": {
                                "contract_version": "geo-scope-v1",
                                "display_type": "HOTSPOT",
                                "label_field": "location",
                                "latitude_field": "latitude",
                                "longitude_field": "longitude",
                            },
                            "aggregation": {
                                "sales": "sum",
                                "revenue_usd": "sum",
                                "fx_usd_cny": "latest",
                                "latitude": "latest",
                                "longitude": "latest",
                            },
                            "visualization_mapping": {
                                "category": "location",
                                "value": "sales",
                            },
                        },
                    },
                    template_kind=TemplateKind.UI_DSL,
                    ui_dsl={
                        "type": "stack",
                        "children": [
                            {
                                "type": "metric",
                                "field": "sales",
                                "label": "Sales",
                            },
                            {
                                "type": "chart",
                                "field": "records",
                                "variant": "area",
                                "x_field": "reported_at",
                                "y_field": "value",
                                "label": "Stored sales reports",
                            },
                            {
                                "type": "timeline",
                                "field": "records",
                                "time_field": "reported_at",
                                "title_field": "label",
                                "value_field": "value",
                                "label": "Report timeline",
                            },
                        ],
                    },
                    visualization_contract={"type": "metric"},
                    extraction_prompt="Extract cited regional sales and coordinates.",
                    model_settings={
                        "extraction_engine": "json_mapping_v1",
                        "field_mappings": {
                            "location": "location",
                            "sales": "sales",
                            "revenue_usd": "revenue_usd",
                            "fx_usd_cny": "fx_usd_cny",
                            "base_currency": "base_currency",
                            "quote_currency": "quote_currency",
                            "rate_basis": "rate_basis",
                            "reported_at": "reported_at",
                            "latitude": "latitude",
                            "longitude": "longitude",
                            "records": "records",
                        },
                    },
                    source_pool_id=pool.id,
                )
                db.add(panel_version)
                await db.flush()

                observation_ids = []
                revenue_ids = []
                fx_rate_ids = []
                store = LocalArtifactStore(Path(temporary_directory))
                for index, publisher in enumerate(("official-a", "official-b")):
                    source = SourceDefinition(
                        pool_id=pool.id,
                        key=f"map-source-{index}-{suffix}",
                        name=f"Map source {index}",
                        canonical_url=f"https://map-{index}.example.test/report",
                        kind=SourceKind.API,
                        global_reputation=1,
                        topic_authority=1,
                        request_config={"publisher_identity": publisher},
                    )
                    db.add(source)
                    await db.flush()
                    job = CollectionJob(
                        source_definition_id=source.id,
                        idempotency_key=f"map:{index}:{suffix}",
                    )
                    db.add(job)
                    await db.commit()
                    source_payload = (
                        '{"location":"Shenzhen","sales":42,'
                        '"revenue_usd":100,"fx_usd_cny":7.2,'
                        '"base_currency":"USD","quote_currency":"CNY",'
                        '"rate_basis":"instant",'
                        '"reported_at":"2026-08-10T00:00:00Z",'
                        '"latitude":22.5431,"longitude":114.0579,'
                        '"records":['
                        '{"reported_at":"2026-08-09T00:00:00Z",'
                        '"label":"Prior report","value":40},'
                        '{"reported_at":"2026-08-10T00:00:00Z",'
                        '"label":"Current report","value":42}],'
                        f'"source_marker":"{publisher}"}}'
                    ).encode()
                    collected = await CollectionService(
                        db,
                        fetcher=FakeFetcher(
                            source_payload,
                            "application/json",
                        ),
                        artifact_store=store,
                    ).run_job(job.id)
                    extracted = await ExtractionService(
                        db,
                        DeterministicMappingProvider(panel_version.model_settings),
                    ).extract(
                        panel_version_id=panel_version.id,
                        snapshot_id=collected.result_snapshot_id,
                    )
                    observations = [
                        await db.get(MetricObservation, item)
                        for item in extracted.observation_ids
                    ]
                    sales = next(
                        item for item in observations if item.metric_key == "sales"
                    )
                    revenue = next(
                        item
                        for item in observations
                        if item.metric_key == "revenue_usd"
                    )
                    fx_rate = next(
                        item
                        for item in observations
                        if item.metric_key == "fx_usd_cny"
                    )
                    observation_ids.append(sales.id)
                    revenue_ids.append(revenue.id)
                    fx_rate_ids.append(fx_rate.id)

                    geography = await db.get(ObservationGeography, sales.id)
                    self.assertEqual(geography.scope["contract_version"], "geo-scope-v1")
                    self.assertEqual(
                        geography.scope["geometry"],
                        {
                            "type": "Point",
                            "coordinates": [
                                Decimal("114.0579"),
                                Decimal("22.5431"),
                            ],
                        },
                    )
                    geography_links = (
                        await db.execute(
                            select(ObservationGeographyEvidence)
                            .where(
                                ObservationGeographyEvidence.observation_id
                                == sales.id
                            )
                            .order_by(ObservationGeographyEvidence.ordinal)
                        )
                    ).scalars().all()
                    self.assertEqual(
                        [item.claim_key for item in geography_links],
                        ["location", "latitude", "longitude"],
                    )

                validation, review = await VerificationService(
                    db
                ).validate_observations(
                    observation_ids,
                    absolute_tolerance=0,
                    relative_tolerance=0,
                )
                self.assertEqual(validation.state, VerificationState.PASSED)
                self.assertIsNone(review)
                assessment = await TrustService(
                    db,
                    artifact_store=store,
                ).assess(
                    observation_id=observation_ids[0],
                    validation_run_id=validation.id,
                )
                self.assertTrue(assessment.eligible)
                second_assessment = await TrustService(
                    db,
                    artifact_store=store,
                ).assess(
                    observation_id=observation_ids[1],
                    validation_run_id=validation.id,
                )
                self.assertTrue(second_assessment.eligible)
                calculated, calculation_run = await VerificationService(db).calculate(
                    operation="add",
                    input_observation_ids=observation_ids,
                    output_metric_key="sales_total",
                    output_unit="vehicle",
                    output_quantum="1",
                    parameters={},
                )
                self.assertEqual(calculated.normalized_value, {"value": "84"})
                calculated_assessment = await TrustService(
                    db,
                    artifact_store=store,
                ).assess(
                    observation_id=calculated.id,
                    validation_run_id=None,
                )
                self.assertTrue(
                    calculated_assessment.eligible,
                    calculated_assessment.reason_codes,
                )
                self.assertEqual(
                    calculated_assessment.calculation_run_id,
                    calculation_run.id,
                )
                converted, conversion_run = await VerificationService(db).convert(
                    input_observation_id=observation_ids[0],
                    kind=ConversionKind.UNIT,
                    output_metric_key="sales_thousands",
                    output_quantum="0.001",
                    to_unit="thousand_vehicle",
                )
                self.assertEqual(converted.normalized_value, {"value": "0.042"})
                converted_assessment = await TrustService(
                    db,
                    artifact_store=store,
                ).assess(
                    observation_id=converted.id,
                    validation_run_id=None,
                )
                self.assertTrue(
                    converted_assessment.eligible,
                    converted_assessment.reason_codes,
                )
                self.assertEqual(
                    converted_assessment.conversion_run_id,
                    conversion_run.id,
                )
                self.assertTrue(
                    await TrustService(db, artifact_store=store).is_assessment_current(
                        converted_assessment
                    )
                )
                revenue_validation, _ = await VerificationService(
                    db
                ).validate_observations(
                    revenue_ids,
                    absolute_tolerance=0,
                    relative_tolerance=0,
                )
                fx_validation, _ = await VerificationService(db).validate_observations(
                    fx_rate_ids,
                    absolute_tolerance=0,
                    relative_tolerance=0,
                )
                for candidate_id in revenue_ids:
                    candidate_assessment = await TrustService(
                        db,
                        artifact_store=store,
                    ).assess(
                        observation_id=candidate_id,
                        validation_run_id=revenue_validation.id,
                    )
                    self.assertTrue(
                        candidate_assessment.eligible,
                        candidate_assessment.reason_codes,
                    )
                for candidate_id in fx_rate_ids:
                    candidate_assessment = await TrustService(
                        db,
                        artifact_store=store,
                    ).assess(
                        observation_id=candidate_id,
                        validation_run_id=fx_validation.id,
                    )
                    self.assertTrue(
                        candidate_assessment.eligible,
                        candidate_assessment.reason_codes,
                    )
                converted_currency, currency_run = await VerificationService(db).convert(
                    input_observation_id=revenue_ids[0],
                    kind=ConversionKind.CURRENCY,
                    output_metric_key="revenue_cny",
                    output_quantum="0.01",
                    to_currency="CNY",
                    fx_rate_observation_id=fx_rate_ids[0],
                )
                self.assertEqual(
                    converted_currency.normalized_value,
                    {"value": "720"},
                )
                currency_assessment = await TrustService(
                    db,
                    artifact_store=store,
                ).assess(
                    observation_id=converted_currency.id,
                    validation_run_id=None,
                )
                self.assertTrue(
                    currency_assessment.eligible,
                    currency_assessment.reason_codes,
                )
                self.assertEqual(
                    currency_assessment.conversion_run_id,
                    currency_run.id,
                )
                geography_replay = await TrustService(
                    db,
                    artifact_store=store,
                ).geography_integrity(
                    await db.get(MetricObservation, observation_ids[0])
                )
                self.assertTrue(geography_replay["accepted"], geography_replay)

                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    insight_response = await client.post(
                        "/api/v2/insights",
                        json={
                            "observation_ids": [str(observation_ids[0])],
                            "created_by": "map-integration-test",
                        },
                    )
                    self.assertEqual(
                        insight_response.status_code,
                        201,
                        insight_response.text,
                    )
                    frozen_features = insight_response.json()["output"][
                        "map_features"
                    ]
                    self.assertEqual(len(frozen_features), 1)
                    self.assertEqual(
                        frozen_features[0]["geometry"]["coordinates"],
                        [114.0579, 22.5431],
                    )
                    map_response = await client.get(
                        "/api/v2/insights/map-features",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(map_response.status_code, 200)
                    payload = map_response.json()
                    self.assertEqual(payload["contract_version"], "trusted-insight-map-v1")
                    self.assertEqual(len(payload["features"]), 1)
                    self.assertEqual(payload["stats"]["current_insights"], 1)
                    self.assertEqual(
                        payload["features"][0]["observation_ids"],
                        [str(observation_ids[0])],
                    )

                    # A newer failed assessment keeps the immutable L2 record,
                    # but immediately removes its feature from the current map.
                    stale_assessment = await TrustService(
                        db,
                        artifact_store=store,
                    ).assess(
                        observation_id=observation_ids[0],
                        validation_run_id=None,
                    )
                    self.assertFalse(stale_assessment.eligible)
                    stale_response = await client.get(
                        "/api/v2/insights/map-features",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(stale_response.status_code, 200)
                    stale_payload = stale_response.json()
                    self.assertEqual(stale_payload["features"], [])
                    self.assertEqual(
                        stale_payload["stats"]["stale_or_invalid_insights"],
                        1,
                    )

    async def test_schema_bound_extraction_creates_cited_metric(self):
        suffix = uuid.uuid4().hex
        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            patch.object(
                settings,
                "ARTIFACT_STORAGE_PATH",
                temporary_directory,
            ),
        ):
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
                    kind=SourceKind.API,
                    global_reputation=1,
                    topic_authority=1,
                    request_config={"publisher_identity": "example-official"},
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
                            "sales": {
                                "type": "integer",
                                "x-unit": "vehicle",
                                "x-uncertainty": {"kind": "exact"},
                            },
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
                    model_settings={
                        "extraction_engine": "json_mapping_v1",
                        "field_mappings": {
                            "brand": "brand",
                            "sales": "sales",
                        },
                    },
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
                        b'{"brand":"BYD","sales":42}',
                        "application/json",
                    ),
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).run_job(job.id)
                captured_fragments = (
                    await db.execute(
                        select(EvidenceFragment).where(
                            EvidenceFragment.snapshot_id
                            == collected.result_snapshot_id
                        )
                    )
                ).scalars().all()
                self.assertEqual(len(captured_fragments), 1)
                fragment = captured_fragments[0]
                original_snapshot = await db.get(
                    SourceSnapshot,
                    collected.result_snapshot_id,
                )
                extracted = await ExtractionService(
                    db,
                    DeterministicMappingProvider(panel_version.model_settings),
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
                evidence_set = await db.get(ObservationEvidenceSet, observation.id)
                self.assertEqual(evidence_set.citation_count, 2)
                observation_links = (
                    await db.execute(
                        select(ObservationEvidenceLink)
                        .where(ObservationEvidenceLink.observation_id == observation.id)
                        .order_by(ObservationEvidenceLink.ordinal)
                    )
                ).scalars().all()
                self.assertEqual(
                    [item.evidence_fragment_id for item in observation_links],
                    [fragment.id, fragment.id],
                )
                self.assertEqual(
                    [item.claim_key for item in observation_links],
                    ["sales", "brand"],
                )
                extraction_link = await db.get(
                    ObservationExtractionLink,
                    observation.id,
                )
                self.assertEqual(extraction_link.extraction_run_id, extracted.run_id)
                self.assertEqual(extraction_link.output_record_ordinal, 0)
                nondeterministic_extracted = await ExtractionService(
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
                nondeterministic_assessment = await TrustService(
                    db,
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).assess(
                    observation_id=nondeterministic_extracted.observation_ids[0],
                    validation_run_id=None,
                )
                self.assertFalse(nondeterministic_assessment.eligible)
                self.assertIn(
                    "DETERMINISTIC_EXTRACTION_REPLAY_FAILED",
                    nondeterministic_assessment.reason_codes,
                )
                independent_source = SourceDefinition(
                    pool_id=pool.id,
                    key=f"independent-{suffix}",
                    name="Independent official source",
                    canonical_url="https://independent.example.test/report",
                    kind=SourceKind.API,
                    global_reputation=1,
                    topic_authority=1,
                    request_config={
                        "publisher_identity": "independent-official"
                    },
                )
                db.add(independent_source)
                await db.flush()
                independent_job = CollectionJob(
                    source_definition_id=independent_source.id,
                    idempotency_key=f"independent:{suffix}",
                )
                db.add(independent_job)
                await db.commit()
                independent_collected = await CollectionService(
                    db,
                    fetcher=FakeFetcher(
                        b'{"brand":"BYD","sales":43}',
                        "application/json",
                    ),
                    artifact_store=LocalArtifactStore(Path(temporary_directory)),
                ).run_job(independent_job.id)
                independent_snapshot = await db.get(
                    SourceSnapshot,
                    independent_collected.result_snapshot_id,
                )
                independent_artifact = await db.get(
                    EvidenceArtifact,
                    independent_snapshot.artifact_id,
                )
                independent_fragments = (
                    await db.execute(
                        select(EvidenceFragment).where(
                            EvidenceFragment.snapshot_id
                            == independent_collected.result_snapshot_id
                        )
                    )
                ).scalars().all()
                self.assertEqual(len(independent_fragments), 1)
                independent_fragment = independent_fragments[0]
                independent_extracted = await ExtractionService(
                    db,
                    DeterministicMappingProvider(panel_version.model_settings),
                ).extract(
                    panel_version_id=panel_version.id,
                    snapshot_id=independent_collected.result_snapshot_id,
                )
                second = await db.get(
                    MetricObservation,
                    independent_extracted.observation_ids[0],
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
                mixed_source = MetricObservation(
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
                originless_peer = MetricObservation(
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
                db.add(same_source)
                db.add(mixed_source)
                db.add(originless_peer)
                await db.flush()
                db.add_all(
                    [
                        ObservationNumericValue(
                            observation_id=item.id,
                            value=item.normalized_value["value"],
                            uncertainty_kind=UncertaintyState.EXACT,
                            absolute_error=0,
                            uncertainty_basis={"kind": "schema_exact"},
                            evidence_count=0,
                        )
                        for item in (same_source, mixed_source, originless_peer)
                    ]
                )
                await db.flush()
                db.add_all(
                    [
                        ObservationEvidenceSet(
                            observation_id=same_source.id,
                            citation_count=1,
                        ),
                        ObservationEvidenceSet(
                            observation_id=mixed_source.id,
                            citation_count=2,
                        ),
                        ObservationEvidenceSet(
                            observation_id=originless_peer.id,
                            citation_count=2,
                        ),
                    ]
                )
                await db.flush()
                db.add_all(
                    [
                        ObservationEvidenceLink(
                            observation_id=mixed_source.id,
                            ordinal=0,
                            evidence_fragment_id=observation.evidence_fragment_id,
                            role="primary",
                            claim_key="sales",
                            field_path="$.sales",
                        ),
                        ObservationEvidenceLink(
                            observation_id=mixed_source.id,
                            ordinal=1,
                            evidence_fragment_id=independent_fragment.id,
                            role="supporting",
                            claim_key="sales",
                            field_path="$.sales",
                        ),
                        ObservationEvidenceLink(
                            observation_id=same_source.id,
                            ordinal=0,
                            evidence_fragment_id=observation.evidence_fragment_id,
                            role="primary",
                            claim_key="sales",
                            field_path="$.sales",
                        ),
                        ObservationEvidenceLink(
                            observation_id=originless_peer.id,
                            ordinal=0,
                            evidence_fragment_id=independent_fragment.id,
                            role="primary",
                            claim_key="sales",
                            field_path="$.sales",
                        ),
                        ObservationEvidenceLink(
                            observation_id=originless_peer.id,
                            ordinal=1,
                            evidence_fragment_id=independent_fragment.id,
                            role="dimension",
                            claim_key="brand",
                            field_path="$.brand",
                        ),
                    ]
                )
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
                mixed_source_validation, mixed_source_review = (
                    await VerificationService(db).validate_observations(
                        [mixed_source.id, second.id],
                        absolute_tolerance=2,
                        relative_tolerance=0,
                    )
                )
                self.assertEqual(
                    mixed_source_validation.state.value,
                    "needs_review",
                )
                self.assertIn(
                    "AMBIGUOUS_OBSERVATION_EVIDENCE_SCOPE",
                    mixed_source_review.reason_codes,
                )
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
                with self.assertRaisesRegex(ValueError, "current eligible assessment"):
                    await VerificationService(db).calculate(
                        operation="add",
                        input_observation_ids=[observation.id, second.id],
                        output_metric_key="combined_sales",
                        output_unit="vehicle",
                        output_quantum="1",
                    )
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
                    direct_observation = next(
                        item
                        for item in observations_response.json()
                        if item["id"] == str(observation.id)
                    )
                    self.assertEqual(direct_observation["lineage"]["state"], "direct")
                    self.assertEqual(
                        direct_observation["lineage"]["origin"]["extraction_run"]["id"],
                        str(extracted.run_id),
                    )
                    self.assertEqual(
                        len(direct_observation["lineage"]["evidence_refs"]),
                        2,
                    )
                    manifest_response = await client.get(
                        f"/api/v2/extractions/{extracted.run_id}/inputs"
                    )
                    self.assertEqual(manifest_response.status_code, 200)
                    manifest_payload = manifest_response.json()
                    self.assertEqual(
                        manifest_payload["status"],
                        "frozen_manifest_present",
                    )
                    self.assertEqual(manifest_payload["input_count"], 1)
                    self.assertEqual(len(manifest_payload["inputs"]), 1)
                    self.assertEqual(
                        manifest_payload["inputs"][0]["evidence_fragment_id"],
                        str(fragment.id),
                    )
                    dashboard_view_response = await client.get(
                        f"/api/v2/dashboards/{dashboard.id}/versions/1/view"
                    )
                    self.assertEqual(dashboard_view_response.status_code, 200)
                    dashboard_panel = dashboard_view_response.json()["panels"][0]
                    self.assertEqual(dashboard_panel["data_state"], "unverified")
                    self.assertEqual(dashboard_panel["data"]["sales"], 43)
                    self.assertEqual(len(dashboard_panel["evidence"]), 1)

                    calculations_response = await client.get(
                        "/api/v2/verification/calculations",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(calculations_response.status_code, 200)
                    self.assertEqual(calculations_response.json(), [])

                    validations_response = await client.get(
                        "/api/v2/verification/validations",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(validations_response.status_code, 200)
                    self.assertEqual(len(validations_response.json()), 4)

                    reviews_response = await client.get(
                        "/api/v2/verification/reviews",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    self.assertEqual(reviews_response.status_code, 200)
                    self.assertEqual(len(reviews_response.json()), 3)
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
                    trusted_observations_response = await client.get(
                        "/api/v2/evidence/observations",
                        params={
                            "panel_version_key": str(panel_version.id),
                            "trusted_only": "true",
                        },
                    )
                    self.assertEqual(trusted_observations_response.status_code, 200)
                    self.assertIn(
                        str(observation.id),
                        {
                            item["id"]
                            for item in trusted_observations_response.json()
                        },
                    )

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
                        "deterministic-stored-summary-v2-map",
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

                    # A corroborating peer revision must immediately stale the
                    # target's historical assessment even though the target
                    # observation itself has not changed.
                    peer_revision_response = await client.post(
                        f"/api/v2/evidence/observations/{second.id}/revisions",
                        json={
                            "raw_value": {"value": 43},
                            "normalized_value": {"value": 43},
                            "reason": "Independent source republished the filing.",
                            "revised_by": "integration-test",
                        },
                    )
                    self.assertEqual(
                        peer_revision_response.status_code,
                        201,
                        peer_revision_response.text,
                    )
                    self.assertFalse(
                        await TrustService(
                            db,
                            artifact_store=LocalArtifactStore(
                                Path(temporary_directory)
                            ),
                        ).is_assessment_current(trust_assessment)
                    )
                    peer_stale_trusted_response = await client.get(
                        "/api/v2/evidence/observations",
                        params={
                            "panel_version_key": str(panel_version.id),
                            "trusted_only": "true",
                        },
                    )
                    self.assertNotIn(
                        str(observation.id),
                        {
                            item["id"]
                            for item in peer_stale_trusted_response.json()
                        },
                    )
                    peer_stale_insight_response = await client.post(
                        "/api/v2/insights",
                        json={
                            "observation_ids": [str(observation.id)],
                            "created_by": "integration-test",
                        },
                    )
                    self.assertEqual(peer_stale_insight_response.status_code, 422)

                    legacy_validation = ValidationRun(
                        comparison_key=validation.comparison_key,
                        observation_ids=validation.observation_ids,
                        rule_version="numeric-v1",
                        tolerance=validation.tolerance,
                        result=validation.result,
                        state=VerificationState.PASSED,
                    )
                    db.add(legacy_validation)
                    await db.commit()
                    legacy_rule_assessment = await TrustService(
                        db,
                        artifact_store=LocalArtifactStore(
                            Path(temporary_directory)
                        ),
                    ).assess(
                        observation_id=observation.id,
                        validation_run_id=legacy_validation.id,
                    )
                    self.assertFalse(legacy_rule_assessment.eligible)
                    self.assertIn(
                        "VALIDATION_RULE_NOT_TRUSTED_BY_CURRENT_POLICY",
                        legacy_rule_assessment.reason_codes,
                    )

                    # A numerically matching row with valid evidence but no
                    # Extraction/Revision/Calculation origin may produce an
                    # immutable ValidationRun, but it must never authorize the
                    # target observation under the current Trust policy.
                    originless_validation, originless_review = (
                        await VerificationService(db).validate_observations(
                            [observation.id, originless_peer.id],
                            absolute_tolerance=2,
                            relative_tolerance=0,
                        )
                    )
                    self.assertEqual(originless_validation.state.value, "passed")
                    self.assertIsNone(originless_review)
                    originless_assessment = await TrustService(
                        db,
                        artifact_store=LocalArtifactStore(
                            Path(temporary_directory)
                        ),
                    ).assess(
                        observation_id=observation.id,
                        validation_run_id=originless_validation.id,
                    )
                    self.assertFalse(originless_assessment.eligible)
                    self.assertIn(
                        "VALIDATION_PEER_TRUST_REPLAY_FAILED",
                        originless_assessment.reason_codes,
                    )
                    self.assertEqual(
                        originless_assessment.details["validation_replay"][
                            "peer_checks"
                        ][str(originless_peer.id)]["origin_count"],
                        0,
                    )

                    # Validation provenance metadata alone is insufficient:
                    # remove only the disposable corroborator bytes and prove
                    # Trust replays every peer artifact instead of trusting the
                    # stored PASSED result.
                    LocalArtifactStore(Path(temporary_directory)).path_for(
                        independent_artifact.sha256
                    ).unlink()
                    missing_artifact_validation, missing_artifact_review = (
                        await VerificationService(db).validate_observations(
                            [observation.id, second.id],
                            absolute_tolerance=2,
                            relative_tolerance=0,
                        )
                    )
                    self.assertEqual(
                        missing_artifact_validation.state.value,
                        "passed",
                    )
                    self.assertIsNone(missing_artifact_review)
                    missing_artifact_assessment = await TrustService(
                        db,
                        artifact_store=LocalArtifactStore(
                            Path(temporary_directory)
                        ),
                    ).assess(
                        observation_id=observation.id,
                        validation_run_id=missing_artifact_validation.id,
                    )
                    self.assertFalse(missing_artifact_assessment.eligible)
                    self.assertIn(
                        "VALIDATION_PEER_TRUST_REPLAY_FAILED",
                        missing_artifact_assessment.reason_codes,
                    )
                    self.assertFalse(
                        missing_artifact_assessment.details["validation_replay"][
                            "peer_checks"
                        ][str(second.id)]["artifact_integrity"]
                    )

                    latest_assessments_response = await client.get(
                        "/api/v2/verification/assessments",
                        params={"panel_version_key": str(panel_version.id)},
                    )
                    initial_after_recheck = next(
                        item
                        for item in latest_assessments_response.json()
                        if item["id"] == str(trust_assessment.id)
                    )
                    self.assertFalse(initial_after_recheck["currently_eligible"])

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

                    string_revision_response = await client.post(
                        f"/api/v2/evidence/observations/{observation.id}/revisions",
                        json={
                            "raw_value": {"value": "44"},
                            "normalized_value": {"value": "44"},
                            "reason": "Invalid string correction.",
                            "revised_by": "integration-test",
                        },
                    )
                    self.assertEqual(string_revision_response.status_code, 422)
                    unit_revision_response = await client.post(
                        f"/api/v2/evidence/observations/{observation.id}/revisions",
                        json={
                            "raw_value": {"value": 44},
                            "normalized_value": {"value": 44},
                            "unit": "thousand_vehicle",
                            "reason": "Invalid implicit conversion.",
                            "revised_by": "integration-test",
                        },
                    )
                    self.assertEqual(unit_revision_response.status_code, 422)

                    revision_response = await client.post(
                        f"/api/v2/evidence/observations/{observation.id}/revisions",
                        json={
                            "raw_value": {"value": 44},
                            "normalized_value": {"value": 44},
                            "reason": "Source issued a correction.",
                            "revised_by": "integration-test",
                            "evidence_claims": {
                                "sales": [str(fragment.id)],
                                "brand": [str(fragment.id)],
                            },
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
                    self.assertIsNone(replacement.extraction_model)
                    replacement_links = (
                        await db.execute(
                            select(ObservationEvidenceLink)
                            .where(
                                ObservationEvidenceLink.observation_id
                                == replacement.id
                            )
                            .order_by(ObservationEvidenceLink.ordinal)
                        )
                    ).scalars().all()
                    self.assertEqual(len(replacement_links), 2)
                    self.assertIsNone(
                        await db.get(ObservationExtractionLink, replacement.id)
                    )
                    replacement_response = await client.get(
                        f"/api/v2/evidence/observations/{replacement.id}"
                    )
                    self.assertEqual(replacement_response.status_code, 200)
                    self.assertEqual(
                        replacement_response.json()["lineage"]["origin"]["kind"],
                        "revision",
                    )

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
                    self.assertEqual(len(revisions_response.json()), 2)
                    self.assertIn(
                        str(replacement.id),
                        {
                            item["replacement_observation_id"]
                            for item in revisions_response.json()
                        },
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
                    stale_trusted_response = await client.get(
                        "/api/v2/evidence/observations",
                        params={
                            "panel_version_key": str(panel_version.id),
                            "trusted_only": "true",
                        },
                    )
                    self.assertNotIn(
                        str(observation.id),
                        {item["id"] for item in stale_trusted_response.json()},
                    )

                    stale_insight_response = await client.post(
                        "/api/v2/insights",
                        json={
                            "observation_ids": [str(observation.id)],
                            "created_by": "integration-test",
                        },
                    )
                    self.assertEqual(stale_insight_response.status_code, 422)

                    # The dashboard keeps the latest failed run auditable but
                    # never promotes its output into the visible metric data.
                    db.add(
                        ExtractionRun(
                            panel_version_id=panel_version.id,
                            snapshot_id=original_snapshot.id,
                            provider="fake",
                            model="invalid-output-test",
                            prompt_version=panel_version.extraction_prompt_version,
                            input_hash="0" * 64,
                            output={
                                "records": [
                                    {
                                        "data": {"brand": "BYD", "sales": 999},
                                        "evidence": {
                                            "brand": [str(fragment.id)],
                                            "sales": [
                                                str(fragment.id),
                                                str(fragment.id),
                                            ],
                                        },
                                    }
                                ]
                            },
                            validation={
                                "valid": False,
                                "issues": [
                                    {
                                        "path": "$.records[0].evidence.sales",
                                        "message": "duplicate citation",
                                    }
                                ],
                            },
                        )
                    )
                    await db.commit()
                    invalid_view_response = await client.get(
                        f"/api/v2/dashboards/{dashboard.id}/versions/1/view"
                    )
                    self.assertEqual(invalid_view_response.status_code, 200)
                    invalid_panel = invalid_view_response.json()["panels"][0]
                    self.assertEqual(invalid_panel["data_state"], "invalid")
                    self.assertIsNone(invalid_panel["data"])
                    self.assertEqual(len(invalid_panel["evidence"]), 1)


if __name__ == "__main__":
    unittest.main()
