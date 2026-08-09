from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.acquisition.parsers import parse_content
from app.ai.providers import (
    DeterministicMappingProvider,
    validate_deterministic_mapping,
)
from app.core.config import settings
from app.domain.evidence import (
    execute_normalized_calculation,
    normalize_calculation_contract,
    sha256_bytes,
    sha256_json,
    validate_locator,
)
from app.domain.map_contract import is_supported_geographic_scope
from app.domain.panel_schema import (
    build_geographic_scope,
    geographic_source_fields,
    validate_observation_contract,
)
from app.models.dashboards import ExtractionRun, PanelVersion
from app.models.evidence import (
    CalculationRun,
    EvidenceArtifact,
    EvidenceFragment,
    ExtractionRunInput,
    ExtractionRunInputSet,
    MetricObservation,
    ObservationEvidenceLink,
    ObservationEvidenceSet,
    ObservationExtractionLink,
    ObservationGeography,
    ObservationGeographyEvidence,
    ObservationRevision,
    ReviewCase,
    ReviewDecision,
    SourceSnapshot,
    TrustAssessment,
    TrustState,
    ValidationRun,
    VerificationState,
)
from app.services.artifact_store import LocalArtifactStore
from app.services.extraction_service import (
    EXTRACTION_CONTRACT_VERSION,
    EXTRACTION_OUTPUT_SCHEMA,
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_input_payload,
    build_extraction_manifest_entry,
    build_extraction_user_prompt,
)
from app.services.verification_service import (
    VALIDATION_RULE_VERSION,
    VerificationService,
)


TRUST_POLICY_VERSION = "trust-eligibility-v3-validation-replay"

# No calculation engine is trusted by this policy yet. In particular,
# decimal-v1 uses the process-global Decimal context and has no error model.
# A future engine must add a real replay implementation here; changing only a
# stored version label can never make a calculation eligible.
TRUSTED_CALCULATION_ENGINE_VERSIONS: frozenset[str] = frozenset()


def _is_finite_json_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return Decimal(str(value)).is_finite()
    except (InvalidOperation, ValueError):
        return False


class TrustService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        artifact_store: LocalArtifactStore | None = None,
    ):
        self.db = db
        self.artifact_store = artifact_store or LocalArtifactStore(
            Path(settings.ARTIFACT_STORAGE_PATH)
        )

    async def _evidence_integrity(
        self,
        observation: MetricObservation,
        *,
        artifact_cache: dict[uuid.UUID, tuple[bool, bytes | None]] | None = None,
        replay_cache: dict[uuid.UUID, tuple[Any, ...] | None] | None = None,
    ) -> dict[str, Any]:
        artifact_cache = artifact_cache if artifact_cache is not None else {}
        replay_cache = replay_cache if replay_cache is not None else {}
        evidence_set = await self.db.get(ObservationEvidenceSet, observation.id)
        links = (
            await self.db.execute(
                select(ObservationEvidenceLink)
                .where(ObservationEvidenceLink.observation_id == observation.id)
                .order_by(ObservationEvidenceLink.ordinal)
            )
        ).scalars().all()
        primary_links = [item for item in links if item.role == "primary"]
        evidence_set_complete = bool(
            evidence_set is not None
            and evidence_set.citation_count == len(links)
            and links
            and [item.ordinal for item in links] == list(range(len(links)))
            and len(primary_links) == 1
            and primary_links[0].ordinal == 0
            and primary_links[0].evidence_fragment_id
            == observation.evidence_fragment_id
            and all(item.claim_key and item.field_path for item in links)
        )

        # Links represent claims, not physical fragments. A single fragment may
        # legitimately support several fields, so every integrity cardinality
        # below is measured against this de-duplicated ID set.
        unique_fragment_ids = {item.evidence_fragment_id for item in links}
        fragments = (
            await self.db.execute(
                select(EvidenceFragment).where(
                    EvidenceFragment.id.in_(unique_fragment_ids)
                )
            )
        ).scalars().all()
        fragment_by_id = {item.id: item for item in fragments}
        snapshot_by_fragment: dict[uuid.UUID, SourceSnapshot] = {}
        snapshot_state_by_fragment: dict[uuid.UUID, bool] = {}
        artifact_by_fragment: dict[uuid.UUID, EvidenceArtifact] = {}
        artifact_integrity_by_id: dict[uuid.UUID, bool] = {}
        fragment_integrity_by_id: dict[uuid.UUID, bool] = {}
        locator_replay_by_id: dict[uuid.UUID, bool] = {}

        for fragment_id in unique_fragment_ids:
            fragment = fragment_by_id.get(fragment_id)
            if fragment is None:
                fragment_integrity_by_id[fragment_id] = False
                locator_replay_by_id[fragment_id] = False
                continue
            snapshot = await self.db.get(SourceSnapshot, fragment.snapshot_id)
            if snapshot is None:
                fragment_integrity_by_id[fragment.id] = False
                locator_replay_by_id[fragment.id] = False
                continue
            snapshot_by_fragment[fragment.id] = snapshot
            snapshot_state_by_fragment[fragment.id] = snapshot.trust_state not in {
                TrustState.REJECTED,
                TrustState.LEGACY_UNVERIFIED,
            }
            artifact = await self.db.get(EvidenceArtifact, snapshot.artifact_id)
            if artifact is None:
                fragment_integrity_by_id[fragment.id] = False
                locator_replay_by_id[fragment.id] = False
                continue
            artifact_by_fragment[fragment.id] = artifact
            if artifact.id not in artifact_cache:
                try:
                    content = self.artifact_store.read(artifact.sha256)
                    integrity = bool(
                        len(content) == artifact.byte_size
                        and sha256_bytes(content) == artifact.sha256
                    )
                    artifact_cache[artifact.id] = (
                        integrity,
                        content if integrity else None,
                    )
                except (OSError, ValueError):
                    artifact_cache[artifact.id] = (False, None)
            artifact_integrity_by_id[artifact.id] = artifact_cache[artifact.id][0]
            fragment_integrity_by_id[fragment.id] = bool(
                fragment.extracted_text is not None
                and fragment.extracted_text_sha256 is not None
                and sha256_bytes(fragment.extracted_text.encode("utf-8"))
                == fragment.extracted_text_sha256
            )
            if artifact_cache[artifact.id][0] is not True:
                locator_replay_by_id[fragment.id] = False
                continue
            source_metadata = (
                snapshot.source_metadata
                if isinstance(snapshot.source_metadata, dict)
                else {}
            )
            parser_kind = source_metadata.get("parser_kind")
            if not isinstance(parser_kind, str):
                locator_replay_by_id[fragment.id] = False
                continue
            try:
                validate_locator(fragment.locator_type, fragment.locator)
                if snapshot.id not in replay_cache:
                    parser_config = (
                        {
                            "record_path": source_metadata.get(
                                "record_path",
                                "",
                            )
                        }
                        if parser_kind == "api"
                        else None
                    )
                    replayed = parse_content(
                        parser_kind,
                        artifact_cache[artifact.id][1],
                        artifact.media_type,
                        parser_config,
                    )
                    replay_cache[snapshot.id] = replayed.records
                replay_records = replay_cache[snapshot.id] or ()
                matches = [
                    record
                    for record in replay_records
                    if record.locator_type == fragment.locator_type
                    and dict(record.locator) == fragment.locator
                ]
                locator_replay_by_id[fragment.id] = bool(
                    len(matches) == 1
                    and matches[0].text == fragment.extracted_text
                )
            except Exception:
                # Parser/runtime failures are evidence failures, never a reason
                # to skip locator replay or trust the stored text.
                replay_cache[snapshot.id] = None
                locator_replay_by_id[fragment.id] = False

        artifact_ids = {item.id for item in artifact_by_fragment.values()}
        artifact_integrity = bool(
            unique_fragment_ids
            and set(artifact_by_fragment) == unique_fragment_ids
            and set(artifact_integrity_by_id) == artifact_ids
            and all(artifact_integrity_by_id.values())
        )
        fragment_integrity = bool(
            unique_fragment_ids
            and set(fragment_integrity_by_id) == unique_fragment_ids
            and all(fragment_integrity_by_id.values())
        )
        locator_replay_integrity = bool(
            unique_fragment_ids
            and set(locator_replay_by_id) == unique_fragment_ids
            and all(locator_replay_by_id.values())
        )
        snapshot_states_eligible = bool(
            unique_fragment_ids
            and set(snapshot_state_by_fragment) == unique_fragment_ids
            and all(snapshot_state_by_fragment.values())
        )
        return {
            "links": links,
            "snapshot_by_fragment": snapshot_by_fragment,
            "evidence_set_complete": evidence_set_complete,
            "evidence_claim_count": len(links),
            "unique_fragment_count": len(unique_fragment_ids),
            "artifact_integrity": artifact_integrity,
            "fragment_integrity": fragment_integrity,
            "locator_replay_integrity": locator_replay_integrity,
            "snapshot_states_eligible": snapshot_states_eligible,
            "artifact_integrity_by_id": {
                str(key): value for key, value in artifact_integrity_by_id.items()
            },
            "fragment_integrity_by_id": {
                str(key): value for key, value in fragment_integrity_by_id.items()
            },
            "locator_replay_by_id": {
                str(key): value for key, value in locator_replay_by_id.items()
            },
            "snapshot_state_by_fragment": {
                str(key): value
                for key, value in snapshot_state_by_fragment.items()
            },
        }

    async def _input_manifest_integrity(
        self,
        extraction_run: ExtractionRun,
    ) -> dict[str, Any]:
        """Replay the exact ordered fragment set supplied to one extraction."""

        input_set = await self.db.get(
            ExtractionRunInputSet,
            extraction_run.id,
        )
        rows = (
            await self.db.execute(
                select(ExtractionRunInput, EvidenceFragment)
                .join(
                    EvidenceFragment,
                    ExtractionRunInput.evidence_fragment_id
                    == EvidenceFragment.id,
                )
                .where(
                    ExtractionRunInput.extraction_run_id == extraction_run.id
                )
                .order_by(ExtractionRunInput.ordinal)
            )
        ).all()
        inputs = [item for item, _fragment in rows]
        fragments = [fragment for _item, fragment in rows]
        ordinals = [item.ordinal for item in inputs]
        validation = (
            extraction_run.validation
            if isinstance(extraction_run.validation, dict)
            else {}
        )
        frozen_count = validation.get("input_manifest_count")
        frozen_hash = validation.get("input_manifest_hash")
        manifest_entries = [
            build_extraction_manifest_entry(
                ordinal=item.ordinal,
                snapshot_id=extraction_run.snapshot_id,
                fragment=fragment,
            )
            for item, fragment in rows
        ]
        structural_complete = bool(
            input_set is not None
            and input_set.input_count > 0
            and input_set.input_count == len(rows)
            and ordinals == list(range(len(rows)))
            and len({item.evidence_fragment_id for item in inputs}) == len(rows)
            and all(
                fragment.snapshot_id == extraction_run.snapshot_id
                and fragment.created_at <= extraction_run.created_at
                and item.extracted_text_sha256
                == fragment.extracted_text_sha256
                and fragment.extracted_text is not None
                and fragment.extracted_text_sha256 is not None
                and sha256_bytes(fragment.extracted_text.encode("utf-8"))
                == fragment.extracted_text_sha256
                for item, fragment in rows
            )
        )
        entry_hashes_match = bool(
            rows
            and all(
                item.manifest_entry_hash == sha256_json(entry)
                for (item, _fragment), entry in zip(
                    rows,
                    manifest_entries,
                    strict=True,
                )
            )
        )
        header_matches = bool(
            not isinstance(frozen_count, bool)
            and isinstance(frozen_count, int)
            and frozen_count == len(rows)
            and isinstance(frozen_hash, str)
            and frozen_hash == sha256_json(manifest_entries)
        )

        artifact_integrity_by_id: dict[uuid.UUID, bool] = {}
        fragment_integrity_by_id: dict[uuid.UUID, bool] = {}
        locator_replay_by_id: dict[uuid.UUID, bool] = {}
        snapshot_state_by_fragment: dict[uuid.UUID, bool] = {}
        artifact_cache: dict[uuid.UUID, tuple[bool, bytes | None]] = {}
        replay_cache: dict[uuid.UUID, tuple[Any, ...] | None] = {}
        for item, fragment in rows:
            fragment_integrity_by_id[fragment.id] = bool(
                fragment.extracted_text is not None
                and fragment.extracted_text_sha256 is not None
                and item.extracted_text_sha256 == fragment.extracted_text_sha256
                and sha256_bytes(fragment.extracted_text.encode("utf-8"))
                == fragment.extracted_text_sha256
            )
            snapshot = await self.db.get(SourceSnapshot, fragment.snapshot_id)
            if snapshot is None:
                snapshot_state_by_fragment[fragment.id] = False
                locator_replay_by_id[fragment.id] = False
                continue
            snapshot_state_by_fragment[fragment.id] = snapshot.trust_state not in {
                TrustState.REJECTED,
                TrustState.LEGACY_UNVERIFIED,
            }
            artifact = await self.db.get(EvidenceArtifact, snapshot.artifact_id)
            if artifact is None:
                locator_replay_by_id[fragment.id] = False
                continue
            if artifact.id not in artifact_cache:
                try:
                    content = self.artifact_store.read(artifact.sha256)
                    integrity = bool(
                        len(content) == artifact.byte_size
                        and sha256_bytes(content) == artifact.sha256
                    )
                    artifact_cache[artifact.id] = (
                        integrity,
                        content if integrity else None,
                    )
                except (OSError, ValueError):
                    artifact_cache[artifact.id] = (False, None)
            artifact_integrity_by_id[artifact.id] = artifact_cache[artifact.id][0]
            if artifact_cache[artifact.id][0] is not True:
                locator_replay_by_id[fragment.id] = False
                continue
            source_metadata = (
                snapshot.source_metadata
                if isinstance(snapshot.source_metadata, dict)
                else {}
            )
            parser_kind = source_metadata.get("parser_kind")
            if not isinstance(parser_kind, str):
                locator_replay_by_id[fragment.id] = False
                continue
            try:
                validate_locator(fragment.locator_type, fragment.locator)
                if snapshot.id not in replay_cache:
                    parser_config = (
                        {"record_path": source_metadata.get("record_path", "")}
                        if parser_kind == "api"
                        else None
                    )
                    replayed = parse_content(
                        parser_kind,
                        artifact_cache[artifact.id][1],
                        artifact.media_type,
                        parser_config,
                    )
                    replay_cache[snapshot.id] = replayed.records
                matches = [
                    record
                    for record in (replay_cache[snapshot.id] or ())
                    if record.locator_type == fragment.locator_type
                    and dict(record.locator) == fragment.locator
                ]
                locator_replay_by_id[fragment.id] = bool(
                    len(matches) == 1
                    and matches[0].text == fragment.extracted_text
                )
            except Exception:
                replay_cache[snapshot.id] = None
                locator_replay_by_id[fragment.id] = False

        artifact_integrity = bool(
            rows
            and artifact_integrity_by_id
            and all(artifact_integrity_by_id.values())
        )
        fragment_integrity = bool(
            rows
            and len(fragment_integrity_by_id) == len(rows)
            and all(fragment_integrity_by_id.values())
        )
        locator_replay_integrity = bool(
            rows
            and len(locator_replay_by_id) == len(rows)
            and all(locator_replay_by_id.values())
        )
        snapshot_states_eligible = bool(
            rows
            and len(snapshot_state_by_fragment) == len(rows)
            and all(snapshot_state_by_fragment.values())
        )
        accepted = bool(
            structural_complete
            and entry_hashes_match
            and header_matches
            and artifact_integrity
            and fragment_integrity
            and locator_replay_integrity
            and snapshot_states_eligible
        )
        return {
            "accepted": accepted,
            "inputs": inputs,
            "fragments": fragments,
            "fragment_ids": {fragment.id for fragment in fragments},
            "structural_complete": structural_complete,
            "entry_hashes_match": entry_hashes_match,
            "header_matches": header_matches,
            "artifact_integrity": artifact_integrity,
            "fragment_integrity": fragment_integrity,
            "locator_replay_integrity": locator_replay_integrity,
            "snapshot_states_eligible": snapshot_states_eligible,
            "input_count": len(rows),
            "manifest_hash": sha256_json(manifest_entries),
        }

    async def _origin_integrity(
        self,
        observation: MetricObservation,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        calculations = (
            await self.db.execute(
                select(CalculationRun).where(
                    CalculationRun.output_observation_id == observation.id
                )
            )
        ).scalars().all()
        revisions = (
            await self.db.execute(
                select(ObservationRevision).where(
                    ObservationRevision.replacement_observation_id == observation.id
                )
            )
        ).scalars().all()
        extraction_rows = (
            await self.db.execute(
                select(ObservationExtractionLink, ExtractionRun)
                .join(
                    ExtractionRun,
                    ObservationExtractionLink.extraction_run_id == ExtractionRun.id,
                )
                .where(ObservationExtractionLink.observation_id == observation.id)
            )
        ).all()
        origin_count = len(calculations) + len(revisions) + len(extraction_rows)
        origin_kind = (
            "ambiguous"
            if origin_count > 1
            else "calculation"
            if calculations
            else "revision"
            if revisions
            else "extraction"
            if extraction_rows
            else "legacy_or_unknown"
        )

        extraction_integrity: bool | None = None
        extraction_input_hash_matches: bool | None = None
        extraction_contract_supported: bool | None = None
        extraction_manifest_integrity: bool | None = None
        extraction_manifest_details: dict[str, Any] | None = None
        deterministic_replay_matches: bool | None = None
        revision_integrity: bool | None = None
        revision_lineage_integrity: bool | None = None
        revision_policy_supported: bool | None = None
        calculation_replay_matches: bool | None = None
        calculation_engine_trusted: bool | None = None
        calculation = calculations[0] if len(calculations) == 1 else None

        if len(extraction_rows) == 1:
            extraction_link, extraction_run = extraction_rows[0]
            extraction_validation = (
                extraction_run.validation
                if isinstance(extraction_run.validation, dict)
                else {}
            )
            panel = await self.db.get(PanelVersion, extraction_run.panel_version_id)
            manifest = await self._input_manifest_integrity(extraction_run)
            run_fragments = manifest["fragments"]
            extraction_manifest_integrity = manifest["accepted"]
            extraction_manifest_details = {
                key: value
                for key, value in manifest.items()
                if key not in {"inputs", "fragments", "fragment_ids"}
            }
            extraction_contract_supported = bool(
                extraction_validation.get("extraction_contract_version")
                == EXTRACTION_CONTRACT_VERSION
            )
            extraction_input_hash_matches = False
            if (
                panel is not None
                and extraction_contract_supported
                and extraction_manifest_integrity
            ):
                expected_input_hash = sha256_json(
                    build_extraction_input_payload(
                        panel=panel,
                        snapshot_id=extraction_run.snapshot_id,
                        fragments=list(run_fragments),
                        provider=extraction_run.provider,
                        model=extraction_run.model,
                    )
                )
                extraction_input_hash_matches = bool(
                    extraction_run.input_hash == expected_input_hash
                )
            panel_settings = (
                panel.model_settings
                if panel is not None and isinstance(panel.model_settings, dict)
                else None
            )
            deterministic_required = bool(
                extraction_run.provider == "deterministic"
                or extraction_run.model == "json-mapping-v1"
                or (
                    panel_settings is not None
                    and panel_settings.get("extraction_engine")
                    == "json_mapping_v1"
                )
            )
            deterministic_replay_matches = None
            if deterministic_required:
                deterministic_replay_matches = False
                if panel is not None and extraction_manifest_integrity:
                    try:
                        validate_deterministic_mapping(panel_settings)
                        replayed = await DeterministicMappingProvider(
                            panel_settings
                        ).generate(
                            system_prompt=EXTRACTION_SYSTEM_PROMPT,
                            user_prompt=build_extraction_user_prompt(
                                panel=panel,
                                fragments=list(run_fragments),
                            ),
                            output_schema=EXTRACTION_OUTPUT_SCHEMA,
                        )
                        deterministic_replay_matches = bool(
                            extraction_run.provider == replayed.provider
                            and extraction_run.model == replayed.model
                            and extraction_run.output == replayed.data
                            and extraction_validation.get("provider_metadata")
                            == replayed.raw_metadata
                        )
                    except (KeyError, TypeError, ValueError):
                        deterministic_replay_matches = False
            records = (
                extraction_run.output.get("records")
                if isinstance(extraction_run.output, dict)
                else None
            )
            record = (
                records[extraction_link.output_record_ordinal]
                if isinstance(records, list)
                and 0 <= extraction_link.output_record_ordinal < len(records)
                else None
            )
            data = record.get("data") if isinstance(record, dict) else None
            citations = record.get("evidence") if isinstance(record, dict) else None
            links: list[ObservationEvidenceLink] = evidence["links"]
            links_by_claim: dict[str, list[str]] = {}
            for link in links:
                links_by_claim.setdefault(link.claim_key, []).append(
                    str(link.evidence_fragment_id)
                )
            citation_integrity = isinstance(citations, dict)
            if citation_integrity:
                for claim_key, linked_ids in links_by_claim.items():
                    frozen_citation = citations.get(claim_key)
                    cited_ids = (
                        [frozen_citation]
                        if isinstance(frozen_citation, str)
                        else frozen_citation
                        if isinstance(frozen_citation, list)
                        and all(isinstance(item, str) for item in frozen_citation)
                        else None
                    )
                    if (
                        cited_ids is None
                        or len(cited_ids) != len(linked_ids)
                        or set(cited_ids) != set(linked_ids)
                    ):
                        citation_integrity = False
                        break
            dimensions_valid = isinstance(observation.dimensions, dict)
            expected_claims = (
                {observation.metric_key, *observation.dimensions.keys()}
                if dimensions_valid
                else set()
            )
            cited_fragments_in_manifest = bool(
                links
                and all(
                    link.evidence_fragment_id in manifest["fragment_ids"]
                    for link in links
                )
            )
            raw_metric_present = bool(
                isinstance(observation.raw_value, dict)
                and "value" in observation.raw_value
            )
            # MetricObservation stores one metric per row under the canonical
            # `value` key; the frozen ExtractionRun stores it under metric_key.
            raw_metric_value = (
                observation.raw_value.get("value")
                if isinstance(observation.raw_value, dict)
                else None
            )
            normalized_metric_value = (
                observation.normalized_value.get("value")
                if isinstance(observation.normalized_value, dict)
                else None
            )
            output_metric_present = bool(
                isinstance(data, dict) and observation.metric_key in data
            )
            metric_values_valid = bool(
                raw_metric_present
                and isinstance(observation.normalized_value, dict)
                and "value" in observation.normalized_value
                and output_metric_present
                and _is_finite_json_number(raw_metric_value)
                and _is_finite_json_number(normalized_metric_value)
                and _is_finite_json_number(data[observation.metric_key])
            )
            schema_contract_integrity = bool(
                panel is not None
                and str(panel.version) == observation.schema_version
                and not validate_observation_contract(
                    panel.data_schema,
                    metric_key=observation.metric_key,
                    raw_value=observation.raw_value,
                    normalized_value=observation.normalized_value,
                    unit=observation.unit,
                    dimensions=observation.dimensions,
                )
            )
            claim_contract_integrity = bool(
                dimensions_valid
                and links
                and all(
                    link.field_path
                    == (
                        f"$.records[{extraction_link.output_record_ordinal}]"
                        f".data.{link.claim_key}"
                    )
                    and (
                        (
                            link.claim_key == observation.metric_key
                            and link.role in {"primary", "supporting"}
                        )
                        or (
                            link.claim_key != observation.metric_key
                            and link.claim_key in observation.dimensions
                            and link.role == "dimension"
                        )
                    )
                    for link in links
                )
            )
            extraction_integrity = bool(
                panel is not None
                and extraction_contract_supported
                and extraction_manifest_integrity
                and extraction_input_hash_matches
                and schema_contract_integrity
                and cited_fragments_in_manifest
                and panel_settings is not None
                and not panel_settings.get("constants")
                and dimensions_valid
                and deterministic_required
                and deterministic_replay_matches is True
                and str(extraction_run.panel_version_id)
                == observation.panel_version_key
                and extraction_run.model == observation.extraction_model
                and extraction_run.prompt_version
                == observation.extraction_prompt_version
                and extraction_validation.get("valid") is True
                and extraction_run.created_at <= observation.created_at
                and evidence["snapshot_by_fragment"]
                and all(
                    snapshot.id == extraction_run.snapshot_id
                    for snapshot in evidence["snapshot_by_fragment"].values()
                )
                and extraction_link.field_path
                == (
                    f"$.records[{extraction_link.output_record_ordinal}]"
                    f".data.{observation.metric_key}"
                )
                and metric_values_valid
                and data[observation.metric_key] == raw_metric_value
                and data[observation.metric_key] == normalized_metric_value
                and all(
                    data.get(key) == value
                    for key, value in observation.dimensions.items()
                )
                and set(links_by_claim) == expected_claims
                and claim_contract_integrity
                and citation_integrity
            )

        if len(revisions) == 1:
            revision = revisions[0]
            original = await self.db.get(
                MetricObservation,
                revision.original_observation_id,
            )
            links = evidence["links"]
            panel = None
            try:
                panel = await self.db.get(
                    PanelVersion,
                    uuid.UUID(observation.panel_version_key),
                )
            except (TypeError, ValueError):
                panel = None
            revision_dimensions_valid = isinstance(observation.dimensions, dict)
            scope_unchanged = bool(
                original is not None
                and revision_dimensions_valid
                and observation.unit == original.unit
                and observation.currency == original.currency
                and observation.observed_at == original.observed_at
                and observation.period_start == original.period_start
                and observation.period_end == original.period_end
                and observation.geographic_scope == original.geographic_scope
                and observation.dimensions == original.dimensions
            )
            revision_contract_integrity = bool(
                panel is not None
                and str(panel.version) == observation.schema_version
                and not validate_observation_contract(
                    panel.data_schema,
                    metric_key=observation.metric_key,
                    raw_value=observation.raw_value,
                    normalized_value=observation.normalized_value,
                    unit=observation.unit,
                    dimensions=observation.dimensions,
                )
            )
            revision_lineage_integrity = bool(
                original is not None
                and revision_dimensions_valid
                and revision.replacement_observation_id == observation.id
                and observation.supersedes_id == revision.original_observation_id
                and observation.panel_version_key == original.panel_version_key
                and observation.schema_version == original.schema_version
                and observation.metric_key == original.metric_key
                and observation.extraction_model is None
                and observation.extraction_prompt_version is None
                and observation.confidence is None
                and {item.claim_key for item in links}
                == {observation.metric_key, *observation.dimensions.keys()}
                and any(
                    item.role == "primary"
                    and item.claim_key == observation.metric_key
                    for item in links
                )
                and all(
                    item.field_path == f"$.revision.claims.{item.claim_key}"
                    and (
                        (
                            item.claim_key == observation.metric_key
                            and item.role in {"primary", "supporting"}
                        )
                        or (
                            item.claim_key in observation.dimensions
                            and item.role == "dimension"
                        )
                    )
                    for item in links
                )
                and scope_unchanged
                and revision_contract_integrity
            )
            # Manual revision provenance is recorded and displayed, but this
            # policy cannot replay human semantic interpretation of a fragment.
            # A future attested correction contract may opt in explicitly.
            revision_policy_supported = False
            revision_integrity = bool(
                revision_lineage_integrity and revision_policy_supported
            )

        if calculation is not None:
            calculation_engine_trusted = (
                calculation.engine_version in TRUSTED_CALCULATION_ENGINE_VERSIONS
            )
            try:
                if not isinstance(calculation.input_observation_ids, list):
                    raise ValueError("calculation input IDs must be an array")
                if not isinstance(calculation.parameters, dict):
                    raise ValueError("calculation parameters must be an object")
                input_ids = [
                    uuid.UUID(str(item)) for item in calculation.input_observation_ids
                ]
                if not input_ids or len(set(input_ids)) != len(input_ids):
                    raise ValueError("calculation input IDs are invalid")
                inputs = [
                    await self.db.get(MetricObservation, input_id)
                    for input_id in input_ids
                ]
                if any(item is None for item in inputs):
                    raise ValueError("calculation input is missing")
                contract = normalize_calculation_contract(
                    calculation.operation,
                    [item.normalized_value["value"] for item in inputs],
                    calculation.parameters,
                )
                replayed = execute_normalized_calculation(contract)
                replay_payload = {
                    "operation": calculation.operation,
                    "input_observation_ids": [str(item.id) for item in inputs],
                    "input_values": [item.normalized_value for item in inputs],
                    "parameters": contract.parameters,
                    "result": str(replayed.value),
                    "engine_version": calculation.engine_version,
                }
                calculation_replay_matches = bool(
                    calculation.output_observation_id == observation.id
                    and calculation.parameters == contract.parameters
                    and calculation.result
                    == {"value": str(replayed.value), "unit": observation.unit}
                    and observation.normalized_value
                    == {"value": str(replayed.value)}
                    and calculation.replay_hash == sha256_json(replay_payload)
                )
            except (KeyError, TypeError, ValueError):
                calculation_replay_matches = False

        lineage_integrity = {
            "extraction": extraction_integrity,
            "revision": revision_integrity,
            "calculation": bool(
                calculation_replay_matches and calculation_engine_trusted
            ) if calculation is not None else None,
        }.get(origin_kind)
        origin_integrity = bool(origin_count == 1 and lineage_integrity is True)
        return {
            "calculation": calculation,
            "origin_count": origin_count,
            "origin_kind": origin_kind,
            "origin_integrity": origin_integrity,
            "extraction_lineage_integrity": extraction_integrity,
            "extraction_contract_version": (
                extraction_validation.get("extraction_contract_version")
                if len(extraction_rows) == 1
                else None
            ),
            "extraction_contract_supported": extraction_contract_supported,
            "extraction_input_hash_matches": extraction_input_hash_matches,
            "extraction_manifest_integrity": extraction_manifest_integrity,
            "extraction_manifest_details": extraction_manifest_details,
            "deterministic_replay_matches": deterministic_replay_matches,
            "revision_lineage_integrity": revision_lineage_integrity,
            "revision_policy_supported": revision_policy_supported,
            "calculation_replay_matches": calculation_replay_matches,
            "calculation_engine_version": (
                calculation.engine_version if calculation is not None else None
            ),
            "calculation_engine_trusted": calculation_engine_trusted,
        }

    async def geography_integrity(
        self,
        observation: MetricObservation,
    ) -> dict[str, Any]:
        """Replay an observation's optional geo-scope-v1 evidence contract."""

        details: dict[str, Any] = {
            "accepted": False,
            "scope": observation.geographic_scope,
            "structural_complete": False,
            "scope_replay_matches": False,
            "citation_replay_matches": False,
            "input_manifest_integrity": False,
            "replay_error": None,
        }
        try:
            scope = observation.geographic_scope
            geography = await self.db.get(ObservationGeography, observation.id)
            links = (
                await self.db.execute(
                    select(ObservationGeographyEvidence)
                    .where(
                        ObservationGeographyEvidence.observation_id
                        == observation.id
                    )
                    .order_by(ObservationGeographyEvidence.ordinal)
                )
            ).scalars().all()
            if scope == {}:
                details["structural_complete"] = geography is None and not links
                return details
            if (
                not isinstance(scope, dict)
                or geography is None
                or geography.scope != scope
                or not is_supported_geographic_scope(scope)
            ):
                return details
            source_fields = set(scope["source_fields"].values())
            links_by_claim: dict[str, list[ObservationGeographyEvidence]] = {}
            for link in links:
                links_by_claim.setdefault(link.claim_key, []).append(link)
            details["structural_complete"] = bool(
                links
                and geography.evidence_count == len(links)
                and [item.ordinal for item in links] == list(range(len(links)))
                and set(links_by_claim) == source_fields
                and all(item.field_path and item.claim_key for item in links)
            )

            extraction_rows = (
                await self.db.execute(
                    select(ObservationExtractionLink, ExtractionRun)
                    .join(
                        ExtractionRun,
                        ObservationExtractionLink.extraction_run_id
                        == ExtractionRun.id,
                    )
                    .where(
                        ObservationExtractionLink.observation_id == observation.id
                    )
                )
            ).all()
            if len(extraction_rows) != 1:
                return details
            extraction_link, extraction_run = extraction_rows[0]
            if extraction_link.match_method != "direct_write":
                return details
            panel = await self.db.get(PanelVersion, extraction_run.panel_version_id)
            if panel is None:
                return details
            validation = (
                extraction_run.validation
                if isinstance(extraction_run.validation, dict)
                else {}
            )
            if (
                validation.get("valid") is not True
                or validation.get("extraction_contract_version")
                != EXTRACTION_CONTRACT_VERSION
                or str(panel.id) != observation.panel_version_key
                or str(panel.version) != observation.schema_version
            ):
                return details
            manifest = await self._input_manifest_integrity(extraction_run)
            details["input_manifest_integrity"] = manifest["accepted"]
            if not manifest["accepted"]:
                return details
            records = (
                extraction_run.output.get("records")
                if isinstance(extraction_run.output, dict)
                else None
            )
            record = (
                records[extraction_link.output_record_ordinal]
                if isinstance(records, list)
                and 0 <= extraction_link.output_record_ordinal < len(records)
                else None
            )
            data = record.get("data") if isinstance(record, dict) else None
            citations = record.get("evidence") if isinstance(record, dict) else None
            if not isinstance(data, dict) or not isinstance(citations, dict):
                return details
            expected_scope = build_geographic_scope(panel.data_schema, data)
            details["scope_replay_matches"] = expected_scope == scope

            expected_fields = set(geographic_source_fields(panel.data_schema))
            citation_replay_matches = bool(
                expected_fields
                and expected_fields == source_fields
                and set(links_by_claim) == expected_fields
            )
            if citation_replay_matches:
                for claim_key, claim_links in links_by_claim.items():
                    citation = citations.get(claim_key)
                    cited_ids = (
                        [citation]
                        if isinstance(citation, str)
                        else citation
                        if isinstance(citation, list)
                        and citation
                        and all(isinstance(item, str) for item in citation)
                        else None
                    )
                    linked_ids = [str(item.evidence_fragment_id) for item in claim_links]
                    if (
                        cited_ids is None
                        or len(cited_ids) != len(linked_ids)
                        or set(cited_ids) != set(linked_ids)
                        or any(
                            item.evidence_fragment_id not in manifest["fragment_ids"]
                            or item.field_path
                            != (
                                f"$.records[{extraction_link.output_record_ordinal}]"
                                f".data.{claim_key}"
                            )
                            for item in claim_links
                        )
                    ):
                        citation_replay_matches = False
                        break
            details["citation_replay_matches"] = citation_replay_matches
            details["accepted"] = bool(
                details["structural_complete"]
                and details["input_manifest_integrity"]
                and details["scope_replay_matches"]
                and details["citation_replay_matches"]
            )
        except (KeyError, LookupError, TypeError, ValueError) as exc:
            details["replay_error"] = str(exc)
        return details

    async def _replay_validation(
        self,
        validation: ValidationRun,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {
            "rule_version": validation.rule_version,
            "expected_rule_version": VALIDATION_RULE_VERSION,
            "rule_supported": validation.rule_version == VALIDATION_RULE_VERSION,
            "replay_error": None,
            "comparison_key_matches": False,
            "result_matches": False,
            "state_matches": False,
            "expected_state": None,
            "expected_result": None,
            "peer_checks": {},
            "accepted": False,
        }
        try:
            replay = await VerificationService(self.db).replay_validation(validation)
            observations: list[MetricObservation] = replay["observations"]
            details["expected_state"] = replay["expected_state"].value
            details["expected_result"] = replay["expected_result"]
            details["comparison_key_matches"] = bool(
                validation.comparison_key == replay["expected_comparison_key"]
            )
            details["result_matches"] = bool(
                validation.result == replay["expected_result"]
            )
            details["state_matches"] = bool(
                validation.state is replay["expected_state"]
            )

            artifact_cache: dict[uuid.UUID, tuple[bool, bytes | None]] = {}
            replay_cache: dict[uuid.UUID, tuple[Any, ...] | None] = {}
            all_peers_trusted = True
            for peer in observations:
                replacement = (
                    await self.db.execute(
                        select(MetricObservation.id)
                        .where(MetricObservation.supersedes_id == peer.id)
                        .limit(1)
                    )
                ).scalar_one_or_none()
                evidence = await self._evidence_integrity(
                    peer,
                    artifact_cache=artifact_cache,
                    replay_cache=replay_cache,
                )
                origin = await self._origin_integrity(peer, evidence)
                state_eligible = peer.trust_state not in {
                    TrustState.REJECTED,
                    TrustState.LEGACY_UNVERIFIED,
                }
                peer_ok = bool(
                    replacement is None
                    and state_eligible
                    and evidence["evidence_set_complete"]
                    and evidence["artifact_integrity"]
                    and evidence["fragment_integrity"]
                    and evidence["locator_replay_integrity"]
                    and evidence["snapshot_states_eligible"]
                    and origin["origin_integrity"]
                )
                all_peers_trusted = all_peers_trusted and peer_ok
                details["peer_checks"][str(peer.id)] = {
                    "current_revision_head": replacement is None,
                    "stored_state_eligible": state_eligible,
                    "evidence_set_complete": evidence["evidence_set_complete"],
                    "evidence_claim_count": evidence["evidence_claim_count"],
                    "unique_fragment_count": evidence["unique_fragment_count"],
                    "artifact_integrity": evidence["artifact_integrity"],
                    "fragment_integrity": evidence["fragment_integrity"],
                    "locator_replay_integrity": evidence[
                        "locator_replay_integrity"
                    ],
                    "snapshot_states_eligible": evidence[
                        "snapshot_states_eligible"
                    ],
                    "origin_kind": origin["origin_kind"],
                    "origin_count": origin["origin_count"],
                    "origin_integrity": origin["origin_integrity"],
                    "extraction_contract_supported": origin[
                        "extraction_contract_supported"
                    ],
                    "extraction_input_hash_matches": origin[
                        "extraction_input_hash_matches"
                    ],
                    "extraction_manifest_integrity": origin[
                        "extraction_manifest_integrity"
                    ],
                    "deterministic_replay_matches": origin[
                        "deterministic_replay_matches"
                    ],
                    "revision_lineage_integrity": origin[
                        "revision_lineage_integrity"
                    ],
                    "revision_policy_supported": origin[
                        "revision_policy_supported"
                    ],
                    "calculation_engine_version": origin[
                        "calculation_engine_version"
                    ],
                    "calculation_replay_matches": origin[
                        "calculation_replay_matches"
                    ],
                    "calculation_engine_trusted": origin[
                        "calculation_engine_trusted"
                    ],
                    "accepted": peer_ok,
                }
            details["all_peers_trusted"] = all_peers_trusted
            details["independent_source_count"] = replay["provenance"][
                "independent_source_count"
            ]
            details["independent_artifact_count"] = replay["provenance"][
                "independent_artifact_count"
            ]
            details["independent_publisher_count"] = replay["provenance"][
                "independent_publisher_count"
            ]
            details["accepted"] = bool(
                details["rule_supported"]
                and details["comparison_key_matches"]
                and details["result_matches"]
                and details["state_matches"]
                and replay["expected_state"] is VerificationState.PASSED
                and validation.state is VerificationState.PASSED
                and all_peers_trusted
            )
        except (KeyError, LookupError, TypeError, ValueError) as exc:
            details["replay_error"] = str(exc)
        return details

    async def is_assessment_current(
        self,
        assessment: TrustAssessment,
    ) -> bool:
        """Dynamically recheck whether an old eligibility decision is current.

        Assessment rows are immutable historical decisions. Current eligibility
        cannot be copied from their stored boolean because any validation peer
        may subsequently be superseded or become invalid under a newer policy.
        """

        if not assessment.eligible or assessment.policy_version != TRUST_POLICY_VERSION:
            return False
        latest_assessment_id = (
            await self.db.execute(
                select(TrustAssessment.id)
                .where(TrustAssessment.observation_id == assessment.observation_id)
                .order_by(desc(TrustAssessment.created_at), desc(TrustAssessment.id))
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest_assessment_id != assessment.id:
            return False
        observation = await self.db.get(
            MetricObservation,
            assessment.observation_id,
        )
        if observation is None:
            return False
        replacement = (
            await self.db.execute(
                select(MetricObservation.id)
                .where(MetricObservation.supersedes_id == observation.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if replacement is not None or assessment.validation_run_id is None:
            return False
        validation = await self.db.get(
            ValidationRun,
            assessment.validation_run_id,
        )
        if (
            validation is None
            or validation.rule_version != VALIDATION_RULE_VERSION
            or not isinstance(validation.observation_ids, list)
            or str(observation.id) not in validation.observation_ids
        ):
            return False
        validation_replay = await self._replay_validation(validation)
        target_peer = validation_replay.get("peer_checks", {}).get(
            str(observation.id),
            {},
        )
        if not validation_replay.get("accepted") or not target_peer.get("accepted"):
            return False
        calculation = (
            await self.db.execute(
                select(CalculationRun)
                .where(CalculationRun.output_observation_id == observation.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if calculation is None:
            return assessment.calculation_run_id is None
        return bool(
            assessment.calculation_run_id == calculation.id
            and calculation.engine_version in TRUSTED_CALCULATION_ENGINE_VERSIONS
        )

    async def assess(
        self,
        *,
        observation_id: uuid.UUID,
        validation_run_id: uuid.UUID | None,
    ) -> TrustAssessment:
        observation = await self.db.get(MetricObservation, observation_id)
        if observation is None:
            raise LookupError("observation not found")
        validation = (
            await self.db.get(ValidationRun, validation_run_id)
            if validation_run_id
            else None
        )
        if validation_run_id and validation is None:
            raise LookupError("validation run not found")
        if validation and (
            not isinstance(validation.observation_ids, list)
            or str(observation.id) not in validation.observation_ids
        ):
            raise ValueError("validation run does not include the observation")

        replacement = (
            await self.db.execute(
                select(MetricObservation)
                .where(MetricObservation.supersedes_id == observation.id)
                .limit(1)
            )
        ).scalar_one_or_none()
        evidence = await self._evidence_integrity(observation)
        origin = await self._origin_integrity(observation, evidence)
        calculation: CalculationRun | None = origin["calculation"]
        validation_replay = (
            await self._replay_validation(validation) if validation else None
        )

        review_decision = None
        if validation:
            review_case = (
                await self.db.execute(
                    select(ReviewCase)
                    .where(ReviewCase.validation_run_id == validation.id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if review_case:
                review_decision = (
                    await self.db.execute(
                        select(ReviewDecision)
                        .where(ReviewDecision.review_case_id == review_case.id)
                        .order_by(desc(ReviewDecision.created_at), desc(ReviewDecision.id))
                        .limit(1)
                    )
                ).scalar_one_or_none()

        reasons: list[str] = []
        if replacement is not None:
            reasons.append("OBSERVATION_SUPERSEDED")
        if observation.trust_state in {
            TrustState.REJECTED,
            TrustState.LEGACY_UNVERIFIED,
        }:
            reasons.append("OBSERVATION_STATE_INELIGIBLE")
        if not evidence["evidence_set_complete"]:
            reasons.append("FROZEN_EVIDENCE_SET_REQUIRED")
        if not evidence["artifact_integrity"]:
            reasons.append("ALL_ARTIFACT_INTEGRITY_NOT_PROVEN")
        if not evidence["fragment_integrity"]:
            reasons.append("ALL_FRAGMENT_INTEGRITY_NOT_PROVEN")
        if not evidence["locator_replay_integrity"]:
            reasons.append("LOCATOR_REPLAY_NOT_PROVEN")
        if not evidence["snapshot_states_eligible"]:
            reasons.append("EVIDENCE_SNAPSHOT_STATE_INELIGIBLE")
        if origin["origin_count"] != 1:
            reasons.append("UNAMBIGUOUS_OBSERVATION_ORIGIN_REQUIRED")
        elif not origin["origin_integrity"]:
            reasons.append("OBSERVATION_ORIGIN_INTEGRITY_NOT_PROVEN")
        if origin["revision_lineage_integrity"] is False:
            reasons.append("REVISION_LINEAGE_INTEGRITY_NOT_PROVEN")
        if (
            origin["origin_kind"] == "extraction"
            and origin["extraction_contract_supported"] is not True
        ):
            reasons.append("EXTRACTION_CONTRACT_NOT_TRUSTED_BY_CURRENT_POLICY")
        if (
            origin["origin_kind"] == "extraction"
            and origin["extraction_input_hash_matches"] is not True
        ):
            reasons.append("EXTRACTION_INPUT_HASH_REPLAY_FAILED")
        if (
            origin["origin_kind"] == "extraction"
            and origin["extraction_manifest_integrity"] is not True
        ):
            reasons.append("EXTRACTION_INPUT_MANIFEST_REPLAY_FAILED")
        if (
            origin["origin_kind"] == "extraction"
            and origin["deterministic_replay_matches"] is False
        ):
            reasons.append("DETERMINISTIC_EXTRACTION_REPLAY_FAILED")
        if (
            origin["origin_kind"] == "extraction"
            and origin["deterministic_replay_matches"] is None
        ):
            reasons.append("NONDETERMINISTIC_EXTRACTION_ATTESTATION_REQUIRED")
        if (
            origin["origin_kind"] == "revision"
            and origin["revision_policy_supported"] is False
        ):
            reasons.append("MANUAL_REVISION_ATTESTATION_NOT_SUPPORTED")
        if calculation is not None and not origin["calculation_engine_trusted"]:
            reasons.append("CALCULATION_ENGINE_NOT_TRUSTED_BY_CURRENT_POLICY")

        if validation is None:
            reasons.append("PASSED_VALIDATION_REQUIRED")
        else:
            assert validation_replay is not None
            if not validation_replay["rule_supported"]:
                reasons.append("VALIDATION_RULE_NOT_TRUSTED_BY_CURRENT_POLICY")
            if validation_replay["replay_error"] is not None:
                reasons.append("VALIDATION_REPLAY_FAILED")
            if not validation_replay["comparison_key_matches"]:
                reasons.append("VALIDATION_COMPARISON_KEY_MISMATCH")
            if not validation_replay["result_matches"]:
                reasons.append("VALIDATION_RESULT_MISMATCH")
            if not validation_replay["state_matches"]:
                reasons.append("VALIDATION_STATE_MISMATCH")
            if validation_replay.get("all_peers_trusted") is not True:
                reasons.append("VALIDATION_PEER_TRUST_REPLAY_FAILED")
            if (
                validation.state is not VerificationState.PASSED
                or validation_replay.get("expected_state")
                != VerificationState.PASSED.value
            ):
                reasons.append("VALIDATION_NOT_PASSED")
            if min(
                validation_replay.get("independent_source_count", 0),
                validation_replay.get("independent_artifact_count", 0),
                validation_replay.get("independent_publisher_count", 0),
            ) < 2:
                reasons.append("INSUFFICIENT_INDEPENDENT_PROVENANCE")
            if not validation_replay["accepted"]:
                reasons.append("VALIDATION_REPLAY_NOT_ACCEPTED")

        assessment = TrustAssessment(
            observation_id=observation.id,
            validation_run_id=validation.id if validation else None,
            calculation_run_id=calculation.id if calculation else None,
            review_decision_id=review_decision.id if review_decision else None,
            eligible=not reasons,
            reason_codes=reasons or ["ELIGIBLE_UNDER_POLICY"],
            policy_version=TRUST_POLICY_VERSION,
            details={
                "current_revision_head": replacement is None,
                "origin_kind": origin["origin_kind"],
                "origin_count": origin["origin_count"],
                "origin_integrity": origin["origin_integrity"],
                "evidence_set_complete": evidence["evidence_set_complete"],
                "evidence_claim_count": evidence["evidence_claim_count"],
                "unique_fragment_count": evidence["unique_fragment_count"],
                "artifact_integrity": evidence["artifact_integrity"],
                "fragment_integrity": evidence["fragment_integrity"],
                "locator_replay_integrity": evidence[
                    "locator_replay_integrity"
                ],
                "snapshot_states_eligible": evidence[
                    "snapshot_states_eligible"
                ],
                "artifact_integrity_by_id": evidence[
                    "artifact_integrity_by_id"
                ],
                "fragment_integrity_by_id": evidence[
                    "fragment_integrity_by_id"
                ],
                "locator_replay_by_id": evidence["locator_replay_by_id"],
                "snapshot_state_by_fragment": evidence[
                    "snapshot_state_by_fragment"
                ],
                "extraction_lineage_integrity": origin[
                    "extraction_lineage_integrity"
                ],
                "extraction_contract_version": origin[
                    "extraction_contract_version"
                ],
                "extraction_contract_supported": origin[
                    "extraction_contract_supported"
                ],
                "extraction_input_hash_matches": origin[
                    "extraction_input_hash_matches"
                ],
                "extraction_manifest_integrity": origin[
                    "extraction_manifest_integrity"
                ],
                "extraction_manifest_details": origin[
                    "extraction_manifest_details"
                ],
                "deterministic_replay_matches": origin[
                    "deterministic_replay_matches"
                ],
                "revision_lineage_integrity": origin[
                    "revision_lineage_integrity"
                ],
                "revision_policy_supported": origin[
                    "revision_policy_supported"
                ],
                "calculation_run_recorded": calculation is not None,
                "calculation_engine_version": origin[
                    "calculation_engine_version"
                ],
                "calculation_replay_matches": origin[
                    "calculation_replay_matches"
                ],
                "calculation_engine_trusted": origin[
                    "calculation_engine_trusted"
                ],
                "validation_state": validation.state.value if validation else None,
                "validation_replay": validation_replay,
                "human_review_outcome": (
                    review_decision.outcome.value if review_decision else None
                ),
                "stored_trust_state": observation.trust_state.value,
            },
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment
