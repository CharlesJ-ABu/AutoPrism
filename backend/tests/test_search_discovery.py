import unittest

import httpx

from app.services.search_discovery_service import (
    GOOGLE_DISCOVERY_ENDPOINT,
    GoogleProgrammableSearchProvider,
    SearchDiscoveryError,
    infer_source_kind,
    normalize_candidate_url,
)


class SearchDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_results_are_normalized_without_returning_credentials(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url).split("?")[0], GOOGLE_DISCOVERY_ENDPOINT)
            self.assertEqual(request.url.params["key"], "ephemeral-key")
            self.assertEqual(request.url.params["cx"], "engine-123")
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "title": "Official PDF",
                            "link": "HTTPS://Example.GOV:443/report.pdf#page=2",
                            "snippet": "Published report",
                            "mime": "application/pdf",
                        },
                        {
                            "title": "Duplicate",
                            "link": "https://example.gov/report.pdf",
                        },
                        {
                            "title": "Unsafe",
                            "link": "file:///private/report.pdf",
                        },
                    ]
                },
                request=request,
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            candidates = await GoogleProgrammableSearchProvider(client).discover(
                api_key="ephemeral-key",
                search_engine_id="engine-123",
                query="official vehicle report",
                limit=10,
                start=1,
                safe="active",
            )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].url, "https://example.gov/report.pdf")
        self.assertEqual(candidates[0].display_host, "example.gov")
        self.assertEqual(candidates[0].suggested_kind, "pdf")
        self.assertNotIn("ephemeral-key", repr(candidates))
        self.assertNotIn("engine-123", repr(candidates))

    async def test_provider_errors_are_sanitized(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={"error": {"message": "key=ephemeral-secret denied"}},
                request=request,
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(SearchDiscoveryError) as raised:
                await GoogleProgrammableSearchProvider(client).discover(
                    api_key="ephemeral-secret",
                    search_engine_id="engine-123",
                    query="official report",
                    limit=5,
                    start=1,
                    safe="active",
                )
        self.assertEqual(
            str(raised.exception),
            "Google denied this search engine or API credential",
        )
        self.assertNotIn("ephemeral-secret", str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)

    def test_url_and_type_contracts_fail_closed(self):
        with self.assertRaises(SearchDiscoveryError):
            normalize_candidate_url("https://user:password@example.com/report")
        with self.assertRaises(SearchDiscoveryError):
            normalize_candidate_url("https://example.com/report?token=secret")
        self.assertEqual(infer_source_kind("https://example.com/data.csv", None), "csv")
        self.assertEqual(
            infer_source_kind(
                "https://example.com/download",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            "xlsx",
        )
        self.assertEqual(infer_source_kind("https://example.com/page", None), "html")


if __name__ == "__main__":
    unittest.main()
