from __future__ import annotations

import uuid

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.sources import (
    CollectionJob,
    CollectionJobState,
    SourceDefinition,
)


class CollectionQueue:
    def __init__(self, client: redis.Redis | None = None):
        self.client = client or redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def enqueue(self, job_id: uuid.UUID) -> None:
        await self.client.lpush(settings.REDIS_QUEUE_NAME, str(job_id))

    async def dequeue(self, timeout: int = 5) -> uuid.UUID | None:
        item = await self.client.brpop(settings.REDIS_QUEUE_NAME, timeout=timeout)
        return uuid.UUID(item[1]) if item else None

    async def close(self) -> None:
        await self.client.aclose()


async def create_collection_job(
    db: AsyncSession,
    queue: CollectionQueue,
    source: SourceDefinition,
    idempotency_key: str,
) -> CollectionJob:
    job = CollectionJob(
        source_definition_id=source.id,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    try:
        await queue.enqueue(job.id)
    except Exception as exc:
        job.state = CollectionJobState.FAILED
        job.error = {
            "code": "QUEUE_UNAVAILABLE",
            "message": str(exc),
        }
        await db.commit()
        raise RuntimeError("collection queue is unavailable") from exc
    return job
