import os
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

from app.core.database import async_engine, get_db
from app.main import app
from app.services.verification_service import observation_numeric_values


class V2ApiInputContractTests(unittest.IsolatedAsyncioTestCase):
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
                                    }
                                },
                                "required": ["count"],
                                "x-autoprism": {
                                    "time_dimension": "snapshot.retrieved_at",
                                    "geographic_dimension": "market",
                                    "aggregation": {"count": "latest"},
                                    "visualization_mapping": {"value": "count"},
                                },
                            },
                            "template_kind": "ui_dsl",
                            "ui_dsl": {
                                "type": "metric",
                                "field": "count",
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

            view_response = await client.get(
                f"/api/v2/dashboards/{dashboard['id']}/versions/1/view"
            )
            self.assertEqual(view_response.status_code, 200, view_response.text)
            view = view_response.json()
            self.assertEqual(view["panels"][0]["data"], None)
            self.assertEqual(view["panels"][0]["evidence"], [])
