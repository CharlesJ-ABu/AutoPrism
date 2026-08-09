import asyncio
import io
import unittest
from decimal import Decimal

import httpx
from openpyxl import Workbook
from pypdf import PdfWriter

from app.acquisition.contracts import AcquisitionBlocked, FetchRequest
from app.acquisition.fetcher import HttpFetcher
from app.acquisition.parsers import (
    parse_content,
    parse_csv,
    parse_html,
    parse_pdf,
    parse_rss,
    parse_xlsx,
)
from app.acquisition.policy import evaluate_robots, evaluate_static_policy


class AcquisitionParserTests(unittest.TestCase):
    def test_json_record_path_preserves_source_pointer(self):
        result = parse_content(
            "api",
            b'{"Count":2,"Results":[{"Make":"A"},{"Make":"B"}]}',
            "application/json",
            {"record_path": "/Results"},
        )
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.records[1].locator, {"pointer": "/Results/1"})
        self.assertEqual(result.records[1].fields, {"Make": "B"})
        precise = parse_content(
            "api",
            b'{"value":0.12345678901234567890123456789}',
            "application/json",
            {},
        )
        self.assertEqual(
            precise.records[0].fields["value"],
            Decimal("0.12345678901234567890123456789"),
        )
        self.assertIn("0.12345678901234567890123456789", precise.records[0].text)

    def test_html_has_reproducible_css_locators(self):
        result = parse_html(
            b"""
            <html><head><title>Official report</title>
            <meta property="article:published_time" content="2026-07-01T10:00:00Z">
            </head><body><main><h1 id="report">Report</h1><p>42 vehicles</p></main></body></html>
            """
        )
        self.assertEqual(result.title, "Official report")
        self.assertEqual(result.published_at.isoformat(), "2026-07-01T10:00:00")
        self.assertEqual(result.records[0].locator, {"selector": "#report"})
        self.assertEqual(result.records[1].text, "42 vehicles")

    def test_csv_and_xlsx_preserve_table_locations(self):
        csv_result = parse_csv("brand,sales\nBYD,42\n".encode())
        self.assertEqual(csv_result.records[0].locator["cell"], "A2")
        self.assertEqual(csv_result.records[0].fields["sales"], "42")

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "销量"
        sheet.append(["品牌", "销量"])
        sheet.append(["BYD", 42])
        buffer = io.BytesIO()
        workbook.save(buffer)
        xlsx_result = parse_xlsx(buffer.getvalue())
        self.assertEqual(xlsx_result.records[0].locator, {"sheet": "销量", "cell": "A2"})
        self.assertEqual(xlsx_result.records[0].fields["销量"], 42)

    def test_rss_and_pdf_locators(self):
        rss = parse_rss(
            b"""<?xml version="1.0"?><rss version="2.0"><channel>
            <title>Official feed</title><item><title>Update</title>
            <link>https://example.test/update</link></item></channel></rss>"""
        )
        self.assertEqual(rss.records[0].locator["xpath"], "/rss/channel/item[1]")

        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buffer = io.BytesIO()
        writer.write(buffer)
        pdf = parse_pdf(buffer.getvalue())
        self.assertEqual(pdf.metadata["page_count"], 1)
        self.assertEqual(pdf.records[0].locator, {"page": 1})

    def test_policy_requires_human_action_for_credentials_and_robots(self):
        missing = evaluate_static_policy(
            "https://example.test/data",
            enabled=True,
            requires_auth=True,
            credential_available=False,
        )
        self.assertFalse(missing.allowed)
        self.assertTrue(missing.requires_human_action)
        robots = evaluate_robots(
            "User-agent: *\nDisallow: /private",
            robots_url="https://example.test/robots.txt",
            target_url="https://example.test/private/data",
            user_agent="AutoPrism/2.0",
        )
        self.assertFalse(robots.allowed)


class HttpFetcherTests(unittest.TestCase):
    def test_fetcher_streams_and_enforces_size(self):
        async def run():
            fetcher = HttpFetcher()
            transport = httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    headers={"content-type": "text/plain; charset=utf-8"},
                    content=b"12345",
                    request=request,
                )
            )
            original_client = httpx.AsyncClient

            class MockClient(httpx.AsyncClient):
                def __init__(self, *args, **kwargs):
                    super().__init__(transport=transport)

            httpx.AsyncClient = MockClient
            try:
                result = await fetcher.fetch(
                    FetchRequest("https://example.test/data", max_bytes=5)
                )
                self.assertEqual(result.content, b"12345")
                with self.assertRaises(AcquisitionBlocked):
                    await fetcher.fetch(
                        FetchRequest("https://example.test/data", max_bytes=4)
                    )
            finally:
                httpx.AsyncClient = original_client

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
