"""Bounded interval scheduler for registered, policy-reviewed sources."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.sources import (
    CollectionJob,
    CollectionJobState,
    RefreshScheduleMode,
    ScheduleDispatch,
    ScheduleDispatchOutcome,
    SourceDefinition,
    SourceRefreshSchedule,
)
from app.services.collection_queue import CollectionQueue, create_collection_job


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def due_bucket(
    schedule: SourceRefreshSchedule,
    observed_at: datetime,
) -> datetime | None:
    if (
        schedule.mode is not RefreshScheduleMode.INTERVAL
        or schedule.interval_seconds is None
        or schedule.interval_seconds < 900
    ):
        return None
    elapsed_seconds = int((observed_at - schedule.created_at).total_seconds())
    if elapsed_seconds < schedule.interval_seconds:
        return None
    bucket_number = elapsed_seconds // schedule.interval_seconds
    return schedule.created_at + timedelta(
        seconds=bucket_number * schedule.interval_seconds
    )


def schedule_bucket_key(schedule_id, due_at: datetime) -> str:
    return f"schedule:{schedule_id}:{int(due_at.replace(tzinfo=timezone.utc).timestamp())}"


class RefreshSchedulerService:
    def __init__(self, db: AsyncSession, queue: CollectionQueue):
        self.db = db
        self.queue = queue

    async def latest_schedules(self) -> list[SourceRefreshSchedule]:
        child = aliased(SourceRefreshSchedule)
        statement = (
            select(SourceRefreshSchedule)
            .where(
                ~exists(
                    select(1).where(
                        child.supersedes_id == SourceRefreshSchedule.id
                    )
                )
            )
            .order_by(SourceRefreshSchedule.created_at, SourceRefreshSchedule.id)
        )
        return list((await self.db.execute(statement)).scalars())

    async def dispatch_due(
        self,
        observed_at: datetime | None = None,
    ) -> list[ScheduleDispatch]:
        now = observed_at or utcnow()
        dispatches: list[ScheduleDispatch] = []
        for schedule in await self.latest_schedules():
            if (
                schedule.mode is not RefreshScheduleMode.INTERVAL
                or not schedule.authorization_attested
            ):
                continue
            due_at = due_bucket(schedule, now)
            if due_at is None:
                continue
            dispatch = await self._dispatch_schedule(schedule, due_at, now)
            if dispatch is not None:
                dispatches.append(dispatch)
        return dispatches

    async def _dispatch_schedule(
        self,
        schedule: SourceRefreshSchedule,
        due_at: datetime,
        observed_at: datetime,
    ) -> ScheduleDispatch | None:
        bucket_key = schedule_bucket_key(schedule.id, due_at)
        existing_dispatch = (
            await self.db.execute(
                select(ScheduleDispatch).where(
                    ScheduleDispatch.bucket_key == bucket_key
                )
            )
        ).scalar_one_or_none()
        if existing_dispatch is not None:
            return None

        source = await self.db.get(SourceDefinition, schedule.source_definition_id)
        if source is None or not source.enabled:
            return await self._record_dispatch(
                schedule,
                bucket_key,
                due_at,
                observed_at,
                ScheduleDispatchOutcome.SKIPPED,
                "SOURCE_DISABLED_OR_MISSING",
                None,
            )

        in_flight = (
            await self.db.execute(
                select(CollectionJob)
                .where(
                    CollectionJob.source_definition_id == source.id,
                    CollectionJob.state.in_(
                        [CollectionJobState.QUEUED, CollectionJobState.RUNNING]
                    ),
                )
                .order_by(CollectionJob.requested_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if in_flight is not None:
            return await self._record_dispatch(
                schedule,
                bucket_key,
                due_at,
                observed_at,
                ScheduleDispatchOutcome.SKIPPED,
                "JOB_IN_FLIGHT",
                in_flight,
            )

        job = (
            await self.db.execute(
                select(CollectionJob).where(
                    CollectionJob.idempotency_key == bucket_key
                )
            )
        ).scalar_one_or_none()
        if job is None:
            try:
                job = await create_collection_job(
                    self.db,
                    self.queue,
                    source,
                    bucket_key,
                )
            except IntegrityError:
                await self.db.rollback()
                job = (
                    await self.db.execute(
                        select(CollectionJob).where(
                            CollectionJob.idempotency_key == bucket_key
                        )
                    )
                ).scalar_one_or_none()
                if job is None:
                    raise
            except RuntimeError:
                job = (
                    await self.db.execute(
                        select(CollectionJob).where(
                            CollectionJob.idempotency_key == bucket_key
                        )
                    )
                ).scalar_one_or_none()
                return await self._record_dispatch(
                    schedule,
                    bucket_key,
                    due_at,
                    observed_at,
                    ScheduleDispatchOutcome.FAILED,
                    "QUEUE_UNAVAILABLE",
                    job,
                )

        outcome = (
            ScheduleDispatchOutcome.QUEUED
            if job.state is CollectionJobState.QUEUED
            else ScheduleDispatchOutcome.FAILED
        )
        reason = "COLLECTION_JOB_QUEUED" if outcome is ScheduleDispatchOutcome.QUEUED else "COLLECTION_JOB_NOT_QUEUED"
        return await self._record_dispatch(
            schedule,
            bucket_key,
            due_at,
            observed_at,
            outcome,
            reason,
            job,
        )

    async def _record_dispatch(
        self,
        schedule: SourceRefreshSchedule,
        bucket_key: str,
        due_at: datetime,
        observed_at: datetime,
        outcome: ScheduleDispatchOutcome,
        reason_code: str,
        job: CollectionJob | None,
    ) -> ScheduleDispatch:
        dispatch = ScheduleDispatch(
            schedule_id=schedule.id,
            source_definition_id=schedule.source_definition_id,
            bucket_key=bucket_key,
            due_at=due_at,
            observed_at=observed_at,
            outcome=outcome,
            reason_code=reason_code,
            collection_job_id=job.id if job else None,
        )
        self.db.add(dispatch)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = (
                await self.db.execute(
                    select(ScheduleDispatch).where(
                        ScheduleDispatch.bucket_key == bucket_key
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                raise
            return existing
        await self.db.refresh(dispatch)
        return dispatch
