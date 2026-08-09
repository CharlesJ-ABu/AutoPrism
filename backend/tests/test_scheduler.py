import os
import unittest
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.database import async_engine, async_session_maker
from app.models.sources import (
    CollectionJob,
    RefreshScheduleMode,
    ScheduleDispatchOutcome,
    SourceDefinition,
    SourceKind,
    SourcePool,
    SourceRefreshSchedule,
)
from app.services.refresh_scheduler_service import (
    RefreshSchedulerService,
    due_bucket,
)


class FakeQueue:
    def __init__(self):
        self.job_ids = []

    async def enqueue(self, job_id):
        self.job_ids.append(job_id)


class RefreshScheduleContractTests(unittest.TestCase):
    def test_interval_bucket_does_not_backfill_missed_runs(self):
        created_at = datetime(2026, 8, 10, 0, 0, 0)
        schedule = SourceRefreshSchedule(
            source_definition_id=uuid.uuid4(),
            mode=RefreshScheduleMode.INTERVAL,
            interval_seconds=900,
            authorization_attested=True,
            actor_label="test",
            created_at=created_at,
        )
        self.assertIsNone(due_bucket(schedule, created_at + timedelta(minutes=14)))
        self.assertEqual(
            due_bucket(schedule, created_at + timedelta(minutes=46)),
            created_at + timedelta(minutes=45),
        )


@unittest.skipUnless(
    os.getenv("AUTOPRISM_RUN_DB_TESTS") == "1",
    "set AUTOPRISM_RUN_DB_TESTS=1 against the disposable test database",
)
class RefreshSchedulerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await async_engine.dispose()

    async def test_due_schedule_dispatches_once_and_history_is_immutable(self):
        suffix = uuid.uuid4().hex
        created_at = datetime(2026, 8, 10, 0, 0, 0)
        async with async_session_maker() as db:
            pool = SourcePool(
                key=f"schedule-pool-{suffix}",
                name="Scheduler pool",
                topic="official updates",
            )
            db.add(pool)
            await db.flush()
            source = SourceDefinition(
                pool_id=pool.id,
                key=f"schedule-source-{suffix}",
                name="Scheduled official source",
                canonical_url="https://example.test/data.json",
                kind=SourceKind.API,
                enabled=True,
                requires_auth=False,
                global_reputation=1,
                topic_authority=1,
            )
            db.add(source)
            await db.flush()
            schedule = SourceRefreshSchedule(
                source_definition_id=source.id,
                mode=RefreshScheduleMode.INTERVAL,
                interval_seconds=900,
                authorization_attested=True,
                actor_label="local-user-self-attested",
                created_at=created_at,
            )
            db.add(schedule)
            await db.commit()
            schedule_id = schedule.id

            queue = FakeQueue()
            service = RefreshSchedulerService(db, queue)
            first = await service.dispatch_due(created_at + timedelta(minutes=16))
            second = await service.dispatch_due(created_at + timedelta(minutes=16))
            matching_first = [item for item in first if item.schedule_id == schedule_id]
            matching_second = [item for item in second if item.schedule_id == schedule_id]
            self.assertEqual(len(matching_first), 1)
            self.assertEqual(
                matching_first[0].outcome,
                ScheduleDispatchOutcome.QUEUED,
            )
            self.assertEqual(matching_second, [])
            job = (
                await db.execute(
                    select(CollectionJob).where(
                        CollectionJob.source_definition_id == source.id
                    )
                )
            ).scalar_one()
            self.assertEqual(job.source_definition_id, source.id)
            self.assertIn(job.id, queue.job_ids)

            other_source = SourceDefinition(
                pool_id=pool.id,
                key=f"other-schedule-source-{suffix}",
                name="Other source",
                canonical_url="https://other.example.test/data.json",
                kind=SourceKind.API,
                enabled=True,
                requires_auth=False,
                global_reputation=1,
                topic_authority=1,
            )
            db.add(other_source)
            await db.commit()
            with self.assertRaises(DBAPIError):
                await db.execute(
                    text(
                        "INSERT INTO schedule_dispatches "
                        "(id, schedule_id, source_definition_id, bucket_key, "
                        "due_at, observed_at, outcome, reason_code) "
                        "VALUES (:id, :schedule_id, :source_id, :bucket_key, "
                        ":due_at, :observed_at, 'SKIPPED', 'INVALID_TEST')"
                    ),
                    {
                        "id": uuid.uuid4(),
                        "schedule_id": schedule_id,
                        "source_id": other_source.id,
                        "bucket_key": f"invalid-source:{uuid.uuid4()}",
                        "due_at": created_at + timedelta(minutes=30),
                        "observed_at": created_at + timedelta(minutes=31),
                    },
                )
                await db.commit()
            await db.rollback()

            with self.assertRaises(DBAPIError):
                await db.execute(
                    text(
                        "UPDATE source_refresh_schedules "
                        "SET actor_label = 'rewritten' WHERE id = :id"
                    ),
                    {"id": schedule_id},
                )
                await db.commit()
            await db.rollback()


if __name__ == "__main__":
    unittest.main()
