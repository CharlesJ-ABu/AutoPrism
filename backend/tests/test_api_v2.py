import os
import unittest
import uuid

import httpx

from app.core.database import async_engine
from app.main import app


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
