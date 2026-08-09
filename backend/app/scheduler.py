from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.services.collection_queue import CollectionQueue
from app.services.refresh_scheduler_service import RefreshSchedulerService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autoprism.scheduler")


async def run_scheduler() -> None:
    queue = CollectionQueue()
    logger.info("AutoPrism V2 refresh scheduler started")
    try:
        while True:
            try:
                async with async_session_maker() as db:
                    dispatches = await RefreshSchedulerService(db, queue).dispatch_due()
                    if dispatches:
                        logger.info("scheduler recorded %d dispatches", len(dispatches))
            except Exception:
                logger.exception("refresh scheduler tick failed; scheduler continues")
            await asyncio.sleep(settings.SCHEDULER_POLL_SECONDS)
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
