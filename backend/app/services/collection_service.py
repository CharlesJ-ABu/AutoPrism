from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acquisition.contracts import AcquisitionBlocked, FetchRequest
from app.acquisition.fetcher import DEFAULT_USER_AGENT, HttpFetcher
from app.acquisition.parsers import parse_content
from app.acquisition.policy import evaluate_robots, evaluate_static_policy
from app.core.config import settings
from app.domain.evidence import sha256_bytes, validate_locator
from app.models.evidence import (
    EvidenceArtifact,
    EvidenceFragment,
    SourceSnapshot,
    TrustState,
)
from app.models.sources import (
    CollectionJob,
    CollectionJobState,
    HumanActionRequest,
    SourceDefinition,
)
from app.services.artifact_store import LocalArtifactStore


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CollectionService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        fetcher: HttpFetcher | None = None,
        artifact_store: LocalArtifactStore | None = None,
    ):
        self.db = db
        self.fetcher = fetcher or HttpFetcher()
        self.artifact_store = artifact_store or LocalArtifactStore(
            Path(settings.ARTIFACT_STORAGE_PATH)
        )

    async def run_job(self, job_id: uuid.UUID) -> CollectionJob:
        job = (
            await self.db.execute(
                select(CollectionJob)
                .where(CollectionJob.id == job_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if job is None:
            raise LookupError(f"collection job not found: {job_id}")
        if job.state in {
            CollectionJobState.RUNNING,
            CollectionJobState.SUCCEEDED,
            CollectionJobState.BLOCKED,
            CollectionJobState.CANCELLED,
        }:
            return job

        source = await self.db.get(SourceDefinition, job.source_definition_id)
        if source is None:
            return await self._fail(job, "SOURCE_NOT_FOUND", "Source no longer exists")

        job.state = CollectionJobState.RUNNING
        job.started_at = utcnow()
        job.attempt_count += 1
        await self.db.commit()

        decision = evaluate_static_policy(
            source.canonical_url,
            enabled=source.enabled,
            requires_auth=source.requires_auth,
            credential_available=bool(source.credential_reference),
        )
        job.policy_result = asdict(decision)
        if not decision.allowed:
            return await self._block(
                job,
                decision.reason_code,
                decision.message,
                decision.requires_human_action,
            )

        try:
            await self._check_robots(source, job)
            request_headers = dict(source.request_config.get("headers", {}))
            result = await self.fetcher.fetch(
                FetchRequest(
                    source.canonical_url,
                    headers=request_headers,
                    timeout_seconds=float(
                        source.request_config.get("timeout_seconds", 30)
                    ),
                    max_bytes=int(
                        source.request_config.get("max_bytes", 25 * 1024 * 1024)
                    ),
                )
            )
            stored = self.artifact_store.put(result.content)
            parsed = parse_content(
                source.kind.value,
                result.content,
                result.media_type,
                source.parser_config,
            )

            artifact = (
                await self.db.execute(
                    select(EvidenceArtifact).where(
                        EvidenceArtifact.sha256 == stored.sha256
                    )
                )
            ).scalar_one_or_none()
            if artifact is None:
                artifact = EvidenceArtifact(
                    sha256=stored.sha256,
                    byte_size=stored.byte_size,
                    media_type=result.media_type,
                    storage_uri=stored.storage_uri,
                )
                self.db.add(artifact)
                await self.db.flush()

            predecessor = (
                await self.db.execute(
                    select(SourceSnapshot)
                    .where(SourceSnapshot.source_definition_id == source.id)
                    .order_by(desc(SourceSnapshot.retrieved_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            configured_publisher = source.request_config.get(
                "publisher_identity"
            )
            publisher_identity = (
                configured_publisher.strip().casefold()
                if isinstance(configured_publisher, str)
                and configured_publisher.strip()
                else None
            )
            snapshot = SourceSnapshot(
                source_definition_id=source.id,
                source_key=source.key,
                canonical_url=result.final_url,
                artifact_id=artifact.id,
                predecessor_id=predecessor.id if predecessor else None,
                retrieved_at=result.retrieved_at,
                published_at=parsed.published_at,
                http_status=result.status_code,
                response_headers=dict(result.headers),
                source_metadata={
                    **dict(parsed.metadata),
                    "title": parsed.title,
                    "requested_url": result.requested_url,
                    "parser_kind": source.kind.value,
                    "publisher_identity": publisher_identity,
                },
                trust_state=TrustState.UNVERIFIED,
            )
            self.db.add(snapshot)
            await self.db.flush()

            for record in parsed.records:
                validate_locator(record.locator_type, record.locator)
                self.db.add(
                    EvidenceFragment(
                        snapshot_id=snapshot.id,
                        locator_type=record.locator_type,
                        locator=dict(record.locator),
                        extracted_text=record.text,
                        extracted_text_sha256=sha256_bytes(
                            record.text.encode("utf-8")
                        ),
                    )
                )

            job.result_snapshot_id = snapshot.id
            job.state = CollectionJobState.SUCCEEDED
            job.finished_at = utcnow()
            job.error = {}
            await self.db.commit()
            await self.db.refresh(job)
            return job
        except AcquisitionBlocked as exc:
            return await self._block(job, exc.reason_code, str(exc), True)
        except Exception as exc:
            await self.db.rollback()
            job = await self.db.get(CollectionJob, job_id)
            if job is None:
                raise
            return await self._fail(job, type(exc).__name__, str(exc))

    async def _check_robots(
        self,
        source: SourceDefinition,
        job: CollectionJob,
    ) -> None:
        if not source.robots_url:
            return
        robots = await self.fetcher.fetch(
            FetchRequest(
                source.robots_url,
                timeout_seconds=float(
                    source.request_config.get("timeout_seconds", 30)
                ),
                max_bytes=1024 * 1024,
            )
        )
        decision = evaluate_robots(
            robots.content.decode("utf-8", errors="replace"),
            robots_url=source.robots_url,
            target_url=source.canonical_url,
            user_agent=DEFAULT_USER_AGENT,
        )
        job.policy_result = asdict(decision)
        if not decision.allowed:
            raise AcquisitionBlocked(decision.reason_code, decision.message)

    async def _block(
        self,
        job: CollectionJob,
        code: str,
        message: str,
        create_action: bool,
    ) -> CollectionJob:
        job.state = CollectionJobState.BLOCKED
        job.finished_at = utcnow()
        job.error = {"code": code, "message": message}
        if create_action:
            self.db.add(
                HumanActionRequest(
                    collection_job_id=job.id,
                    reason_code=code,
                    instructions=message,
                    context={"source_definition_id": str(job.source_definition_id)},
                )
            )
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _fail(
        self,
        job: CollectionJob,
        code: str,
        message: str,
    ) -> CollectionJob:
        job.state = CollectionJobState.FAILED
        job.finished_at = utcnow()
        job.error = {"code": code, "message": message}
        await self.db.commit()
        await self.db.refresh(job)
        return job
