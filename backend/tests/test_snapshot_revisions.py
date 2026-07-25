from dataclasses import dataclass, field
import asyncio
import uuid

from app.models.sql import RawIntelligence
from app.services.crawler_service import CrawlerService


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


@dataclass
class FakeSession:
    latest: RawIntelligence | None = None
    added: list = field(default_factory=list)
    commits: int = 0

    async def execute(self, _statement):
        return ScalarResult(self.latest)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


def raw(content: str) -> RawIntelligence:
    return RawIntelligence(
        id=uuid.uuid4(),
        source_url="https://example.com/source",
        source_name="legacy_unverified:test",
        title="Source",
        raw_content=content,
        target_panel_ids=["p1"],
    )


def test_changed_content_appends_revision() -> None:
    session = FakeSession()
    service = CrawlerService(session)
    first = raw("v1")
    assert asyncio.run(service._persist_snapshots([first], "p1")) == 1
    assert first.revision == 1
    assert first.content_hash

    session.latest = first
    session.added.clear()
    second = raw("v2")
    assert asyncio.run(service._persist_snapshots([second], "p1")) == 1
    assert second.revision == 2
    assert second.supersedes_id == first.id


def test_unchanged_content_is_not_duplicated() -> None:
    session = FakeSession()
    service = CrawlerService(session)
    first = raw("same")
    asyncio.run(service._persist_snapshots([first], "p1"))
    session.latest = first
    session.added.clear()

    duplicate = raw("same")
    assert asyncio.run(service._persist_snapshots([duplicate], "p1")) == 0
    assert session.added == []
