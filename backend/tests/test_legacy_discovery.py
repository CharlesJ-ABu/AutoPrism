import asyncio

from app.services.scrapers.specialized import SpecializedScraper


class FakeAI:
    async def _call_ai(self, _prompt: str):
        return [
            {
                "title": "Missing source",
                "source_name": "Unknown",
                "content": "Must be discarded",
            },
            {
                "title": "Traceable candidate",
                "source_name": "Official source",
                "source_url": "https://example.com/notice",
                "content": "Candidate content",
            },
        ]


def test_discovery_never_fabricates_urls() -> None:
    results = asyncio.run(
        SpecializedScraper._ai_driven_search(
            FakeAI(), "p1", "policy", ["notice"]
        )
    )
    assert len(results) == 1
    assert results[0].source_url == "https://example.com/notice"
    assert results[0].source_name == "legacy_unverified:Official source"
