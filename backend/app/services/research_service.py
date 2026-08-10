from __future__ import annotations

import math
import uuid
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import exists, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import StructuredModelProvider
from app.domain.evidence import canonical_json, sha256_bytes, sha256_json
from app.models.research import (
    ResearchAction,
    ResearchActionEvent,
    ResearchActionType,
    ResearchEventType,
    ResearchPlan,
    ResearchRun,
)
from app.models.sources import SourceDefinition, SourcePool


RESEARCH_PLAN_PROMPT_VERSION = "research-plan-v1"
RESEARCH_PLAN_SYSTEM_PROMPT = """You are the research planner for AutoPrism.
Create a bounded plan for the user's research objective using only the supplied
database inventory. You may propose Google discovery queries and may select
registered sources by their exact source_key. Never claim that a source was
searched, collected, validated, or read. Never output factual findings,
measurements, prices, rates, formulas with values, default values, NA values, or
invented URLs. Tool actions are proposals only and always require explicit user
authorization. Prefer official primary sources and independent publishers.
State analysis targets and interpretation questions, but leave arithmetic to
the deterministic calculation engine and trust decisions to validation code.
Return only the requested JSON object."""

QuestionText = Annotated[str, Field(min_length=3, max_length=1000)]
ExpectedFieldName = Annotated[
    str,
    Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"),
]


class DiscoveryProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=3, max_length=500)
    purpose: str = Field(min_length=3, max_length=1000)
    limit: int = Field(default=5, ge=1, le=10)


class CollectionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_key: str = Field(min_length=1, max_length=255)
    purpose: str = Field(min_length=3, max_length=1000)


class AnalysisTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    question: str = Field(min_length=3, max_length=1000)
    expected_fields: list[ExpectedFieldName] = Field(min_length=1, max_length=20)
    evidence_expectation: str = Field(min_length=3, max_length=1000)
    requires_cross_source: bool = True


class ResearchPlanDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=3, max_length=2000)
    research_questions: list[QuestionText] = Field(min_length=1, max_length=12)
    discovery_actions: list[DiscoveryProposal] = Field(default_factory=list, max_length=10)
    collection_actions: list[CollectionProposal] = Field(default_factory=list, max_length=10)
    analysis_targets: list[AnalysisTarget] = Field(min_length=1, max_length=12)
    interpretation_questions: list[QuestionText] = Field(min_length=1, max_length=12)
    limitations: list[QuestionText] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def validate_action_count(self):
        count = len(self.discovery_actions) + len(self.collection_actions)
        if count < 1 or count > 20:
            raise ValueError("research plan requires between 1 and 20 tool actions")
        return self


RESEARCH_PLAN_OUTPUT_SCHEMA = ResearchPlanDocument.model_json_schema()


def build_research_input_manifest(
    *,
    inventory: dict[str, Any],
    provider_name: str,
    model_name: str,
    provider_config_hash: str,
) -> dict[str, Any]:
    return {
        "prompt_version": RESEARCH_PLAN_PROMPT_VERSION,
        "system_prompt": RESEARCH_PLAN_SYSTEM_PROMPT,
        "inventory": inventory,
        "provider": provider_name,
        "model": model_name,
        "provider_config_hash": provider_config_hash,
    }


def build_research_user_prompt(inventory: dict[str, Any]) -> str:
    return (
        "Create an auditable research plan from this database inventory:\n"
        + canonical_json(inventory)
    )


def build_research_action_payloads(
    document: ResearchPlanDocument,
    source_inventory: list[dict[str, Any]],
) -> list[tuple[ResearchActionType, dict[str, Any]]]:
    source_by_key = {
        item.get("source_key"): item
        for item in source_inventory
        if isinstance(item, dict) and isinstance(item.get("source_key"), str)
    }
    payloads: list[tuple[ResearchActionType, dict[str, Any]]] = []
    for item in document.discovery_actions:
        payloads.append(
            (
                ResearchActionType.DISCOVER,
                {
                    "query": item.query.strip(),
                    "purpose": item.purpose,
                    "limit": item.limit,
                    "safe": "active",
                },
            )
        )
    for item in document.collection_actions:
        source = source_by_key.get(item.source_key)
        if source is None:
            raise ValueError(f"research plan selected unknown source key: {item.source_key}")
        source_id = source.get("source_definition_id")
        source_name = source.get("name")
        if not isinstance(source_id, str) or not isinstance(source_name, str):
            raise ValueError("research source inventory is incomplete")
        payloads.append(
            (
                ResearchActionType.COLLECT,
                {
                    "source_definition_id": source_id,
                    "source_key": item.source_key,
                    "source_name": source_name,
                    "purpose": item.purpose,
                },
            )
        )
    return payloads


def _safe_model_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    response_id = value.get("id")
    if isinstance(response_id, str):
        output["response_id_sha256"] = sha256_bytes(response_id.encode("utf-8"))
    usage = value.get("usage")
    if isinstance(usage, dict):
        output["usage"] = {
            str(key)[:100]: item
            for key, item in usage.items()
            if isinstance(item, (int, float))
            and not isinstance(item, bool)
            and (not isinstance(item, float) or math.isfinite(item))
        }
    return output


class ResearchPlanningService:
    def __init__(self, db: AsyncSession, provider: StructuredModelProvider):
        self.db = db
        self.provider = provider

    async def create_plan(
        self,
        *,
        pool: SourcePool,
        title: str,
        objective: str,
        constraints: dict[str, Any],
        provider_name: str,
        model_name: str,
        provider_config_hash: str,
    ) -> tuple[ResearchRun, ResearchPlan, list[ResearchAction]]:
        if len(provider_config_hash) != 64 or any(
            character not in "0123456789abcdef" for character in provider_config_hash
        ):
            raise ValueError("provider configuration hash is invalid")
        sources = list(
            (
                await self.db.execute(
                    select(SourceDefinition)
                    .where(SourceDefinition.pool_id == pool.id)
                    .order_by(SourceDefinition.key)
                )
            ).scalars()
        )
        inventory = {
            "research": {
                "title": title,
                "objective": objective,
                "constraints": constraints,
            },
            "source_pool": {
                "id": str(pool.id),
                "key": pool.key,
                "name": pool.name,
                "topic": pool.topic,
                "default_discovery_query": pool.discovery_query,
            },
            "registered_sources": [
                {
                    "source_definition_id": str(source.id),
                    "source_key": source.key,
                    "name": source.name,
                    "kind": source.kind.value,
                    "enabled": source.enabled,
                    "requires_auth": source.requires_auth,
                    "global_reputation": source.global_reputation,
                    "topic_authority": source.topic_authority,
                }
                for source in sources
            ],
        }
        input_manifest = build_research_input_manifest(
            inventory=inventory,
            provider_name=provider_name,
            model_name=model_name,
            provider_config_hash=provider_config_hash,
        )
        response = await self.provider.generate(
            system_prompt=RESEARCH_PLAN_SYSTEM_PROMPT,
            user_prompt=build_research_user_prompt(inventory),
            output_schema=RESEARCH_PLAN_OUTPUT_SCHEMA,
        )
        if (
            not isinstance(response.provider, str)
            or not response.provider.strip()
            or len(response.provider) > 100
            or not isinstance(response.model, str)
            or not response.model.strip()
            or len(response.model) > 255
        ):
            raise ValueError("model provider returned invalid identity metadata")
        document = ResearchPlanDocument.model_validate(response.data)
        source_by_key = {source.key: source for source in sources}
        requested_source_keys = [item.source_key for item in document.collection_actions]
        if len(set(requested_source_keys)) != len(requested_source_keys):
            raise ValueError("research plan repeated a collection source")
        unknown = sorted(set(requested_source_keys) - set(source_by_key))
        if unknown:
            raise ValueError(
                "research plan selected unknown source keys: " + ", ".join(unknown)
            )
        disabled = sorted(
            key for key in requested_source_keys if not source_by_key[key].enabled
        )
        if disabled:
            raise ValueError(
                "research plan selected disabled source keys: " + ", ".join(disabled)
            )
        queries = [item.query.strip() for item in document.discovery_actions]
        if len(set(queries)) != len(queries):
            raise ValueError("research plan repeated a discovery query")

        frozen_plan = document.model_dump(mode="json")
        actions_payload = build_research_action_payloads(
            document,
            inventory["registered_sources"],
        )

        run = ResearchRun(
            source_pool_id=pool.id,
            title=title,
            objective=objective,
            constraints=constraints,
            actor_label="local-user-self-attested",
        )
        self.db.add(run)
        await self.db.flush()
        plan = ResearchPlan(
            run_id=run.id,
            provider=response.provider or provider_name,
            model=response.model or model_name,
            prompt_version=RESEARCH_PLAN_PROMPT_VERSION,
            system_prompt_sha256=sha256_bytes(
                RESEARCH_PLAN_SYSTEM_PROMPT.encode("utf-8")
            ),
            input_hash=sha256_json(input_manifest),
            input_manifest=input_manifest,
            output_hash=sha256_json(frozen_plan),
            plan=frozen_plan,
            action_count=len(actions_payload),
            model_metadata=_safe_model_metadata(response.raw_metadata),
        )
        self.db.add(plan)
        await self.db.flush()
        actions: list[ResearchAction] = []
        for ordinal, (action_type, specification) in enumerate(actions_payload):
            action = ResearchAction(
                run_id=run.id,
                plan_id=plan.id,
                ordinal=ordinal,
                action_type=action_type,
                specification=specification,
                requires_authorization=True,
            )
            self.db.add(action)
            actions.append(action)
        await self.db.flush()
        self.db.add_all(
            [
                ResearchActionEvent(
                    action_id=action.id,
                    run_id=run.id,
                    event_type=ResearchEventType.PROPOSED,
                    actor_label="llm-plan-proposal",
                    details={"action_type": action.action_type.value},
                )
                for action in actions
            ]
        )
        await self.db.commit()
        return run, plan, actions


ALLOWED_EVENT_TRANSITIONS: dict[ResearchEventType, set[ResearchEventType]] = {
    ResearchEventType.PROPOSED: {
        ResearchEventType.AUTHORIZED,
        ResearchEventType.BLOCKED,
    },
    ResearchEventType.AUTHORIZED: {ResearchEventType.STARTED},
    ResearchEventType.STARTED: {
        ResearchEventType.COMPLETED,
        ResearchEventType.QUEUED,
        ResearchEventType.BLOCKED,
        ResearchEventType.FAILED,
    },
    ResearchEventType.BLOCKED: {ResearchEventType.AUTHORIZED},
    ResearchEventType.FAILED: {ResearchEventType.AUTHORIZED},
    ResearchEventType.QUEUED: set(),
    ResearchEventType.COMPLETED: set(),
}


class ResearchActionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def current_event(self, action_id: uuid.UUID) -> ResearchActionEvent:
        successor = aliased(ResearchActionEvent)
        event = (
            await self.db.execute(
                select(ResearchActionEvent)
                .where(ResearchActionEvent.action_id == action_id)
                .where(
                    ~exists().where(
                        successor.predecessor_id == ResearchActionEvent.id
                    )
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if event is None:
            raise LookupError("research action has no state event")
        return event

    async def append_event(
        self,
        *,
        action: ResearchAction,
        event_type: ResearchEventType,
        actor_label: Literal[
            "local-user-self-attested",
            "autoprism-research-orchestrator",
        ],
        details: dict[str, Any],
    ) -> ResearchActionEvent:
        previous = await self.current_event(action.id)
        if event_type not in ALLOWED_EVENT_TRANSITIONS[previous.event_type]:
            raise ValueError(
                f"research action cannot transition from {previous.event_type.value} "
                f"to {event_type.value}"
            )
        event = ResearchActionEvent(
            action_id=action.id,
            run_id=action.run_id,
            event_type=event_type,
            actor_label=actor_label,
            details=details,
            predecessor_id=previous.id,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
