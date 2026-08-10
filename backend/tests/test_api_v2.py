import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.database import async_engine, async_session_maker, get_db
from app.main import app
from app.api.v2.dashboards import (
    CUSTOM_RUNTIME_VERSION,
    PanelVersionCreate,
    validate_custom_component_contract,
)
from app.models.dashboards import TemplateKind
from app.services.search_discovery_service import DiscoveryCandidate
from app.services.verification_service import observation_numeric_values


class V2ApiInputContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_research_provider_and_nonfinite_constraints_are_422(self):
        class FakeSession:
            async def get(self, model, identity):
                return SimpleNamespace(id=identity)

        async def override_get_db():
            yield FakeSession()

        app.dependency_overrides[get_db] = override_get_db
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                unsupported = await client.post(
                    "/api/v2/research/runs",
                    json={
                        "source_pool_id": str(uuid.uuid4()),
                        "title": "Research plan",
                        "objective": "Create an auditable official-source research plan.",
                        "provider": "unsupported-provider",
                        "model": "test-model",
                    },
                )
                nonfinite = await client.post(
                    "/api/v2/research/runs",
                    json={
                        "source_pool_id": str(uuid.uuid4()),
                        "title": "Research plan",
                        "objective": "Create an auditable official-source research plan.",
                        "constraints": {"threshold": float("nan")},
                    },
                )
                interpretation = await client.post(
                    "/api/v2/research/interpretations",
                    json={
                        "title": "Evidence interpretation",
                        "question": "What can the selected trusted observation support?",
                        "observation_ids": [str(uuid.uuid4())],
                        "created_by": "local-user-self-attested",
                        "provider": "unsupported-provider",
                        "model": "test-model",
                    },
                )
            self.assertEqual(unsupported.status_code, 422, unsupported.text)
            self.assertEqual(nonfinite.status_code, 422, nonfinite.text)
            self.assertEqual(interpretation.status_code, 422, interpretation.text)
            self.assertEqual(
                nonfinite.json()["detail"],
                "research constraints must be finite canonical JSON",
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_custom_component_contract_is_fail_closed(self):
        base = {
            "key": "custom-panel",
            "title": "Custom panel",
            "data_schema": {"type": "object", "properties": {}},
            "template_kind": TemplateKind.CUSTOM_REACT,
            "ui_dsl": {"type": "stack", "children": []},
            "visualization_contract": {
                "runtime": CUSTOM_RUNTIME_VERSION,
                "dependencies": [],
            },
        }
        accepted = PanelVersionCreate(
            **base,
            component_code="export default function Panel() { return <div>ok</div>; }",
        )
        validate_custom_component_contract(accepted)

        rejected = [
            {**base, "component_code": None},
            {
                **base,
                "component_code": "export default function Panel() { return null; }",
                "visualization_contract": {"runtime": "unsafe", "dependencies": []},
            },
            {
                **base,
                "component_code": (
                    "import React from 'react'; "
                    "export default function Panel() { return null; }"
                ),
            },
            {
                **base,
                "component_code": "function Panel() { return null; }",
            },
        ]
        for payload in rejected:
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(Exception, "custom React panel"):
                    validate_custom_component_contract(PanelVersionCreate(**payload))

    def test_historical_normalized_value_shape_fails_closed(self):
        for malformed in (None, [], {}, {"other": 1}, {"value": None}):
            with self.subTest(normalized_value=malformed):
                observation = SimpleNamespace(
                    id=uuid.uuid4(),
                    normalized_value=malformed,
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "lacks a canonical normalized value",
                ):
                    observation_numeric_values([observation])

    async def test_calculation_contract_errors_are_422_before_database_work(self):
        observation_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        invalid_payloads = [
            {
                "operation": "not-an-operation",
                "parameters": {},
            },
            {
                "operation": "add",
                "parameters": {"weights": [1, 1]},
            },
            {
                "operation": "weighted_average",
                "parameters": {"weights": ["1", "1"]},
            },
            {
                "operation": "multiply",
                "parameters": {"unit_plan": "vehicle*currency"},
            },
            {
                "operation": "divide",
                "parameters": {"unit_plan": {}},
            },
        ]
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            for invalid in invalid_payloads:
                with self.subTest(payload=invalid):
                    response = await client.post(
                        "/api/v2/verification/calculate",
                        json={
                            "operation": invalid["operation"],
                            "input_observation_ids": observation_ids,
                            "output_metric_key": "derived_metric",
                            "output_unit": "vehicle",
                            "output_quantum": "1",
                            "parameters": invalid["parameters"],
                        },
                    )
                    self.assertEqual(response.status_code, 422, response.text)

    async def test_verification_type_errors_are_422(self):
        observation_id = str(uuid.uuid4())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            with patch(
                "app.api.v2.verification.VerificationService.calculate",
                new=AsyncMock(side_effect=TypeError("malformed normalized value")),
            ):
                calculation_response = await client.post(
                    "/api/v2/verification/calculate",
                    json={
                        "operation": "add",
                        "input_observation_ids": [observation_id],
                        "output_metric_key": "derived_metric",
                        "output_unit": "vehicle",
                        "output_quantum": "1",
                        "parameters": {},
                    },
                )
            with patch(
                "app.api.v2.verification.VerificationService.validate_observations",
                new=AsyncMock(side_effect=TypeError("malformed normalized value")),
            ):
                validation_response = await client.post(
                    "/api/v2/verification/validate",
                    json={
                        "observation_ids": [observation_id],
                        "absolute_tolerance": "0",
                        "relative_tolerance": "0",
                    },
                )
        self.assertEqual(calculation_response.status_code, 422)
        self.assertEqual(validation_response.status_code, 422)

    async def test_conversion_contract_is_fail_closed_before_database_work(self):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            registry = await client.get("/api/v2/verification/unit-registry")
            invalid = await client.post(
                "/api/v2/verification/conversions",
                json={
                    "input_observation_id": str(uuid.uuid4()),
                    "kind": "currency",
                    "output_metric_key": "revenue_cny",
                    "output_quantum": "0.01",
                    "to_currency": "CNY",
                },
            )
        self.assertEqual(registry.status_code, 200, registry.text)
        self.assertEqual(registry.json()["version"], "unit-registry-v1")
        self.assertTrue(
            any(item["code"] == "thousand_vehicle" for item in registry.json()["units"])
        )
        self.assertEqual(invalid.status_code, 422, invalid.text)

    async def test_extraction_service_value_error_is_422(self):
        panel_version_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()

        class FakeSession:
            async def get(self, model, identity):
                return SimpleNamespace(
                    model_settings={
                        "extraction_engine": "json_mapping_v1",
                        "field_mappings": {"value": "value"},
                    }
                )

        async def override_get_db():
            yield FakeSession()

        app.dependency_overrides[get_db] = override_get_db
        try:
            with patch(
                "app.api.v2.extractions.ExtractionService.extract",
                new=AsyncMock(
                    side_effect=ValueError(
                        "rejected or legacy snapshot cannot be extracted"
                    )
                ),
            ):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/api/v2/extractions",
                        json={
                            "panel_version_id": str(panel_version_id),
                            "snapshot_id": str(snapshot_id),
                        },
                    )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(
                response.json()["detail"],
                "rejected or legacy snapshot cannot be extracted",
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

    async def test_invalid_deterministic_mapping_is_422(self):
        class FakeSession:
            async def get(self, model, identity):
                return SimpleNamespace(
                    model_settings={
                        "extraction_engine": "json_mapping_v1",
                        "constants": {"fabricated": 1},
                    }
                )

        async def override_get_db():
            yield FakeSession()

        app.dependency_overrides[get_db] = override_get_db
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v2/extractions",
                    json={
                        "panel_version_id": str(uuid.uuid4()),
                        "snapshot_id": str(uuid.uuid4()),
                    },
                )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(
                response.json()["detail"],
                "deterministic extraction constants are forbidden",
            )
        finally:
            app.dependency_overrides.pop(get_db, None)

    async def test_historical_non_object_model_settings_is_422(self):
        class FakeSession:
            async def get(self, model, identity):
                return SimpleNamespace(model_settings=[])

        async def override_get_db():
            yield FakeSession()

        app.dependency_overrides[get_db] = override_get_db
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v2/extractions",
                    json={
                        "panel_version_id": str(uuid.uuid4()),
                        "snapshot_id": str(uuid.uuid4()),
                    },
                )
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(
                response.json()["detail"],
                "panel model_settings must be an object",
            )
        finally:
            app.dependency_overrides.pop(get_db, None)


@unittest.skipUnless(
    os.getenv("AUTOPRISM_RUN_DB_TESTS") == "1",
    "set AUTOPRISM_RUN_DB_TESTS=1 against the disposable test database",
)
class V2ApiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await async_engine.dispose()

    async def test_search_discovery_persists_candidates_without_credentials(self):
        suffix = uuid.uuid4().hex
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            pool_response = await client.post(
                "/api/v2/sources/pools",
                json={
                    "key": f"discovery-{suffix}",
                    "name": "Discovery test",
                    "topic": "official vehicle data",
                    "discovery_query": "site:example.gov vehicle report",
                },
            )
            self.assertEqual(pool_response.status_code, 201, pool_response.text)
            pool = pool_response.json()
            with patch(
                "app.services.search_discovery_service."
                "GoogleProgrammableSearchProvider.discover",
                new=AsyncMock(
                    return_value=[
                        DiscoveryCandidate(
                            title="Official report",
                            url="https://example.gov/report.pdf",
                            display_host="example.gov",
                            snippet="Published source",
                            mime_type="application/pdf",
                            suggested_kind="pdf",
                        )
                    ]
                ),
            ):
                response = await client.post(
                    f"/api/v2/sources/pools/{pool['id']}/discover",
                    json={
                        "api_key": "must-not-persist",
                        "search_engine_id": "engine-must-not-persist",
                        "safe": "active",
                    },
                )
            self.assertEqual(response.status_code, 201, response.text)
            payload = response.json()
            self.assertEqual(payload["result_count"], 1)
            self.assertTrue(payload["integrity_valid"])
            self.assertEqual(payload["candidates"][0]["suggested_kind"], "pdf")
            self.assertNotIn("must-not-persist", response.text)

            history = await client.get(
                f"/api/v2/sources/discovery-runs?pool_id={pool['id']}"
            )
            self.assertEqual(history.status_code, 200, history.text)
            self.assertEqual(len(history.json()), 1)
            self.assertEqual(history.json()[0]["result_hash"], payload["result_hash"])
            self.assertTrue(history.json()[0]["integrity_valid"])
            self.assertNotIn("must-not-persist", history.text)

        async with async_session_maker() as db:
            frozen_text = (
                await db.execute(
                    text(
                        "SELECT query || provider_config_hash || result_hash "
                        "FROM source_discovery_runs WHERE id = :run_id"
                    ),
                    {"run_id": payload["id"]},
                )
            ).scalar_one()
            self.assertNotIn("must-not-persist", frozen_text)
            with self.assertRaises(DBAPIError):
                await db.execute(
                    text(
                        "UPDATE source_discovery_runs SET query = 'rewritten' "
                        "WHERE id = :run_id"
                    ),
                    {"run_id": payload["id"]},
                )
                await db.commit()
            await db.rollback()
            with self.assertRaises(DBAPIError):
                await db.execute(text("TRUNCATE source_discovery_runs CASCADE"))
                await db.commit()
            await db.rollback()
            with self.assertRaises(DBAPIError):
                await db.execute(
                    text(
                        "INSERT INTO source_discovery_candidates "
                        "(id, run_id, ordinal, title, url, url_sha256, "
                        "display_host, snippet, mime_type, suggested_kind, created_at) "
                        "VALUES (:id, :run_id, 1, 'late result', "
                        "'https://example.gov/late', :url_hash, 'example.gov', "
                        "'', NULL, 'html', now())"
                    ),
                    {
                        "id": uuid.uuid4(),
                        "run_id": payload["id"],
                        "url_hash": "0" * 64,
                    },
                )
                await db.commit()
            await db.rollback()

    async def test_refresh_schedule_versions_require_explicit_authorization(self):
        suffix = uuid.uuid4().hex
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            pool_response = await client.post(
                "/api/v2/sources/pools",
                json={
                    "key": f"schedule-api-{suffix}",
                    "name": "Schedule API pool",
                    "topic": "official updates",
                },
            )
            self.assertEqual(pool_response.status_code, 201, pool_response.text)
            source_response = await client.post(
                f"/api/v2/sources/pools/{pool_response.json()['id']}",
                json={
                    "key": f"schedule-source-{suffix}",
                    "name": "Scheduled source",
                    "canonical_url": "https://example.test/data.json",
                    "kind": "api",
                    "global_reputation": 1,
                    "topic_authority": 1,
                },
            )
            self.assertEqual(source_response.status_code, 201, source_response.text)
            source_id = source_response.json()["id"]

            manual = await client.post(
                f"/api/v2/sources/{source_id}/refresh-schedules",
                json={"mode": "manual", "authorization_confirmed": False},
            )
            self.assertEqual(manual.status_code, 201, manual.text)
            rejected = await client.post(
                f"/api/v2/sources/{source_id}/refresh-schedules",
                json={"mode": "interval", "interval_minutes": 60},
            )
            self.assertEqual(rejected.status_code, 422, rejected.text)
            interval = await client.post(
                f"/api/v2/sources/{source_id}/refresh-schedules",
                json={
                    "mode": "interval",
                    "interval_minutes": 60,
                    "authorization_confirmed": True,
                },
            )
            self.assertEqual(interval.status_code, 201, interval.text)
            self.assertEqual(interval.json()["supersedes_id"], manual.json()["id"])

            history = await client.get(
                f"/api/v2/sources/refresh-schedules?source_id={source_id}"
            )
            self.assertEqual(history.status_code, 200, history.text)
            self.assertEqual(len(history.json()), 2)
            current = [item for item in history.json() if item["current"]]
            self.assertEqual(len(current), 1)
            self.assertEqual(current[0]["id"], interval.json()["id"])

    async def test_source_and_versioned_dashboard_contracts(self):
        suffix = uuid.uuid4().hex
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            pool_response = await client.post(
                "/api/v2/sources/pools",
                json={
                    "key": f"api-pool-{suffix}",
                    "name": "API Contract Pool",
                    "topic": "Automotive",
                },
            )
            self.assertEqual(pool_response.status_code, 201, pool_response.text)
            pool = pool_response.json()
            source_response = await client.post(
                f"/api/v2/sources/pools/{pool['id']}",
                json={
                    "key": "official-api",
                    "name": "Official API",
                    "canonical_url": "https://example.test/data.json",
                    "kind": "api",
                    "global_reputation": 1,
                    "topic_authority": 1,
                },
            )
            self.assertEqual(source_response.status_code, 201, source_response.text)
            self.assertEqual(source_response.json()["kind"], "api")

            dashboard_response = await client.post(
                "/api/v2/dashboards",
                json={
                    "key": f"api-dashboard-{suffix}",
                    "title": "API Dashboard",
                    "description": "Contract test",
                },
            )
            self.assertEqual(
                dashboard_response.status_code,
                201,
                dashboard_response.text,
            )
            dashboard = dashboard_response.json()
            version_response = await client.post(
                f"/api/v2/dashboards/{dashboard['id']}/versions",
                json={
                    "state": "draft",
                    "panels": [
                        {
                            "key": "registrations",
                            "title": "Registrations",
                            "data_schema": {
                                "$schema": "https://json-schema.org/draft/2020-12/schema",
                                "type": "object",
                                "properties": {
                                    "count": {
                                        "type": "integer",
                                        "x-unit": "vehicle",
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
                                "required": ["count", "records"],
                                "x-autoprism": {
                                    "time_dimension": "snapshot.retrieved_at",
                                    "geographic_dimension": "market",
                                    "aggregation": {"count": "latest"},
                                    "visualization_mapping": {"value": "count"},
                                },
                            },
                            "template_kind": "ui_dsl",
                            "ui_dsl": {
                                "type": "stack",
                                "children": [
                                    {"type": "metric", "field": "count"},
                                    {
                                        "type": "chart",
                                        "field": "records",
                                        "variant": "line",
                                        "x_field": "reported_at",
                                        "y_field": "value",
                                        "series_field": "label",
                                        "max_series": 4,
                                    },
                                    {
                                        "type": "timeline",
                                        "field": "records",
                                        "time_field": "reported_at",
                                        "title_field": "label",
                                        "value_field": "value",
                                    },
                                ],
                            },
                            "source_pool_id": pool["id"],
                        }
                    ],
                },
            )
            self.assertEqual(version_response.status_code, 201, version_response.text)
            version = version_response.json()
            self.assertEqual(version["version"], 1)
            self.assertEqual(version["panels"][0]["template_kind"], "ui_dsl")

            history_response = await client.get(
                f"/api/v2/dashboards/{dashboard['id']}/versions"
            )
            self.assertEqual(
                history_response.status_code,
                200,
                history_response.text,
            )
            history = history_response.json()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["version"], 1)
            self.assertEqual(history[0]["state"], "draft")
            self.assertEqual(history[0]["panel_count"], 1)

            detail_response = await client.get(
                f"/api/v2/dashboards/{dashboard['id']}/versions/1"
            )
            self.assertEqual(
                detail_response.status_code,
                200,
                detail_response.text,
            )
            detail = detail_response.json()
            self.assertEqual(detail["panels"][0]["key"], "registrations")
            self.assertIn("data_schema", detail["panels"][0])
            self.assertIn("ui_dsl", detail["panels"][0])
            self.assertEqual(
                detail["panels"][0]["ui_dsl"]["children"][1]["series_field"],
                "label",
            )

            view_response = await client.get(
                f"/api/v2/dashboards/{dashboard['id']}/versions/1/view"
            )
            self.assertEqual(view_response.status_code, 200, view_response.text)
            view = view_response.json()
            self.assertEqual(view["panels"][0]["data"], None)
            self.assertEqual(view["panels"][0]["evidence"], [])
