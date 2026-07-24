from __future__ import annotations

import asyncio
import logging

from app.core.database import async_session_maker
from app.services.collection_queue import CollectionQueue
from app.services.collection_service import CollectionService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autoprism.worker")


async def run_worker() -> None:
    queue = CollectionQueue()
    logger.info("AutoPrism V2 collection worker started")
    try:
        while True:
            job_id = await queue.dequeue()
            if job_id is None:
                continue
            async with async_session_maker() as db:
                try:
                    job = await CollectionService(db).run_job(job_id)
                    logger.info(
                        "collection job %s finished as %s",
                        job.id,
                        job.state.value,
                    )
                except Exception:
                    logger.exception(
                        "collection job %s raised an unhandled error; worker continues",
                        job_id,
                    )
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
