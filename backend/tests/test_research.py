import os
import unittest
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError

from app.ai.providers import StructuredModelResponse
from app.core.database import async_engine, async_session_maker
from app.domain.evidence import canonical_json, sha256_json
from app.models.research import (
    EvidenceInterpretation,
    EvidenceInterpretationInput,
    ResearchAction,
    ResearchActionEvent,
    ResearchEventType,
    ResearchPlan,
    ResearchRun,
    _reject_research_mutation,
)
from app.models.sources import SourceDefinition, SourceKind, SourcePool
from app.services.research_service import (
    RESEARCH_PLAN_OUTPUT_SCHEMA,
    RESEARCH_PLAN_PROMPT_VERSION,
    RESEARCH_PLAN_SYSTEM_PROMPT,
    ResearchActionService,
    ResearchPlanDocument,
    ResearchPlanningService,
    build_research_input_manifest,
    build_research_user_prompt,
)
from app.services.interpretation_service import (
    INTERPRETATION_OUTPUT_SCHEMA,
    INTERPRETATION_SYSTEM_PROMPT,
    InterpretationDocument,
    InterpretationService,
    _validate_document,
)


class FakeResearchProvider:
    def __init__(self, data):
        self.data = data
        self.calls = []

    async def generate(self, *, system_prompt, user_prompt, output_schema):
        self.calls.append((system_prompt, user_prompt, output_schema))
        return StructuredModelResponse(
            data=self.data,
            provider="fake-provider",
            model="fake-model-v1",
            raw_metadata={
                "id": "response-1",
                "usage": {"input_tokens": 123},
                "credential": "must-not-persist",
            },
        )


def valid_plan(source_key: str) -> dict:
    return {
        "summary": "Collect official releases and compare independent evidence.",
        "research_questions": ["What has the publisher reported?"],
        "discovery_actions": [
            {
                "query": "site:example.test official report",
                "purpose": "Find a primary publication not yet registered.",
                "limit": 5,
            }
        ],
        "collection_actions": [
            {
                "source_key": source_key,
                "purpose": "Collect the registered primary source.",
            }
        ],
        "analysis_targets": [
            {
                "key": "reported_metric",
                "question": "What value is explicitly reported?",
                "expected_fields": ["value", "unit", "period"],
                "evidence_expectation": "A locator-backed primary-source claim.",
                "requires_cross_source": True,
            }
        ],
        "interpretation_questions": ["Do independent publishers agree?"],
        "limitations": ["No result is trusted until tools execute and validate it."],
    }


class ResearchPlanContractTests(unittest.TestCase):
    def test_research_and_interpretation_models_are_append_only(self):
        for model in (
            ResearchRun,
            ResearchPlan,
            ResearchAction,
            ResearchActionEvent,
            EvidenceInterpretation,
            EvidenceInterpretationInput,
        ):
            with self.subTest(model=model.__name__):
                self.assertTrue(
                    event.contains(model, "before_update", _reject_research_mutation)
                )
                self.assertTrue(
                    event.contains(model, "before_delete", _reject_research_mutation)
                )

    def test_prompt_and_schema_forbid_model_execution_claims(self):
        self.assertIn("Never claim", RESEARCH_PLAN_SYSTEM_PROMPT)
        self.assertIn("Never output factual findings", RESEARCH_PLAN_SYSTEM_PROMPT)
        self.assertIn("explicit user", RESEARCH_PLAN_SYSTEM_PROMPT)
        self.assertEqual(RESEARCH_PLAN_OUTPUT_SCHEMA["additionalProperties"], False)

        inventory = {"source_pool": {"key": "alpha"}, "registered_sources": []}
        prompt = build_research_user_prompt(inventory)
        self.assertEqual(prompt.split("\n", 1)[1], canonical_json(inventory))
        manifest = build_research_input_manifest(
            inventory=inventory,
            provider_name="openai",
            model_name="gpt-test",
            provider_config_hash="a" * 64,
        )
        self.assertEqual(manifest["prompt_version"], RESEARCH_PLAN_PROMPT_VERSION)
        self.assertEqual(manifest["inventory"], inventory)
        self.assertEqual(manifest["provider_config_hash"], "a" * 64)

    def test_plan_requires_at_least_one_bounded_action(self):
        payload = valid_plan("official")
        payload["discovery_actions"] = []
        payload["collection_actions"] = []
        with self.assertRaises(ValueError):
            ResearchPlanDocument.model_validate(payload)

    def test_interpretation_requires_exact_input_pairs_and_cited_numbers(self):
        observation_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        allowed_pairs = {observation_id: assessment_id}
        numeric_values = {observation_id: Decimal("42")}
        base = {
            "summary": "The selected evidence supports a bounded interpretation.",
            "claims": [
                {
                    "statement": "The stored value is 42 vehicles.",
                    "observation_ids": [str(observation_id)],
                    "trust_assessment_ids": [str(assessment_id)],
                    "reasoning": "The cited normalized value is 42.",
                    "limitation": "This statement does not establish a forecast.",
                }
            ],
            "limitations": ["Model narrative does not change trust eligibility."],
        }
        document = InterpretationDocument.model_validate(base)
        _validate_document(document, allowed_pairs, numeric_values)
        self.assertIn("do not calculate", INTERPRETATION_SYSTEM_PROMPT)
        self.assertEqual(INTERPRETATION_OUTPUT_SCHEMA["additionalProperties"], False)

        uncited = {**base, "claims": [{**base["claims"][0], "statement": "The value is 43."}]}
        with self.assertRaisesRegex(ValueError, "uncited numeric value"):
            _validate_document(
                InterpretationDocument.model_validate(uncited),
                allowed_pairs,
                numeric_values,
            )

        wrong_pair = {
            **base,
            "claims": [
                {
                    **base["claims"][0],
                    "trust_assessment_ids": [str(uuid.uuid4())],
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "unavailable input pair"):
            _validate_document(
                InterpretationDocument.model_validate(wrong_pair),
                allowed_pairs,
                numeric_values,
            )


class InterpretationEligibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_noncurrent_assessment_is_rejected_before_model_or_persistence(self):
        observation_id = uuid.uuid4()
        observation = SimpleNamespace(
            id=observation_id,
            normalized_value={"value": 42},
        )
        assessment = SimpleNamespace(id=uuid.uuid4(), observation_id=observation_id)
        result = SimpleNamespace(scalar_one_or_none=lambda: assessment)
        db = SimpleNamespace(
            get=AsyncMock(return_value=observation),
            execute=AsyncMock(return_value=result),
        )
        provider = SimpleNamespace(generate=AsyncMock())
        with patch(
            "app.services.interpretation_service.TrustService.is_assessment_current",
            AsyncMock(return_value=False),
        ):
            with self.assertRaisesRegex(ValueError, "current eligible"):
                await InterpretationService(db, provider)._load_inputs([observation_id])
        provider.generate.assert_not_awaited()


@unittest.skipUnless(
    os.getenv("AUTOPRISM_RUN_DB_TESTS") == "1",
    "set AUTOPRISM_RUN_DB_TESTS=1 against the disposable test database",
)
class ResearchPlanIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        await async_engine.dispose()

    async def test_plan_is_frozen_allowlisted_and_event_history_is_immutable(self):
        suffix = uuid.uuid4().hex
        async with async_session_maker() as db:
            pool = SourcePool(
                key=f"research-pool-{suffix}",
                name="Research pool",
                topic="official reports",
            )
            db.add(pool)
            await db.flush()
            source = SourceDefinition(
                pool_id=pool.id,
                key=f"official-{suffix}",
                name="Official source",
                canonical_url="https://example.test/report.json",
                kind=SourceKind.API,
                enabled=True,
                requires_auth=False,
                global_reputation=1,
                topic_authority=1,
            )
            db.add(source)
            await db.commit()
            pool_id = pool.id

            provider = FakeResearchProvider(valid_plan(source.key))
            run, plan, actions = await ResearchPlanningService(db, provider).create_plan(
                pool=pool,
                title="Official metric research",
                objective="Build a sourced comparison of the official reported metric.",
                constraints={"period": "2026-Q2"},
                provider_name="fake-provider",
                model_name="fake-model-v1",
                provider_config_hash="b" * 64,
            )

            self.assertEqual(len(actions), 2)
            self.assertEqual([action.ordinal for action in actions], [0, 1])
            self.assertTrue(all(action.requires_authorization for action in actions))
            self.assertEqual(plan.input_hash, sha256_json(plan.input_manifest))
            self.assertNotIn("credential", canonical_json(plan.input_manifest))
            self.assertNotIn("https://", canonical_json(plan.input_manifest))
            self.assertNotIn("must-not-persist", canonical_json(plan.model_metadata))
            self.assertEqual(provider.calls[0][0], RESEARCH_PLAN_SYSTEM_PROMPT)
            self.assertIn(canonical_json({"period": "2026-Q2"}), provider.calls[0][1])

            root_events = list(
                (
                    await db.execute(
                        select(ResearchActionEvent).where(
                            ResearchActionEvent.run_id == run.id
                        )
                    )
                ).scalars()
            )
            self.assertEqual(len(root_events), 2)
            self.assertTrue(
                all(event.event_type == ResearchEventType.PROPOSED for event in root_events)
            )

            action_service = ResearchActionService(db)
            await action_service.append_event(
                action=actions[0],
                event_type=ResearchEventType.AUTHORIZED,
                actor_label="local-user-self-attested",
                details={"authorization_confirmed": True},
            )
            await action_service.append_event(
                action=actions[0],
                event_type=ResearchEventType.STARTED,
                actor_label="autoprism-research-orchestrator",
                details={"action_type": "discover"},
            )
            completed = await action_service.append_event(
                action=actions[0],
                event_type=ResearchEventType.COMPLETED,
                actor_label="autoprism-research-orchestrator",
                details={"result_count": 0},
            )
            self.assertEqual((await action_service.current_event(actions[0].id)).id, completed.id)
            with self.assertRaises(ValueError):
                await action_service.append_event(
                    action=actions[0],
                    event_type=ResearchEventType.AUTHORIZED,
                    actor_label="local-user-self-attested",
                    details={},
                )

            with self.assertRaises(DBAPIError):
                await db.execute(
                    text("UPDATE research_plans SET model = 'rewritten' WHERE id = :id"),
                    {"id": plan.id},
                )
                await db.commit()
            await db.rollback()
            pool = await db.get(SourcePool, pool_id)
            self.assertIsNotNone(pool)

            before_count = (
                await db.execute(select(func.count()).select_from(ResearchRun))
            ).scalar_one()
            invalid_provider = FakeResearchProvider(valid_plan("unknown-source"))
            with self.assertRaisesRegex(ValueError, "unknown source keys"):
                await ResearchPlanningService(db, invalid_provider).create_plan(
                    pool=pool,
                    title="Invalid source plan",
                    objective="Try to select an unregistered source without guessing.",
                    constraints={},
                    provider_name="fake-provider",
                    model_name="fake-model-v1",
                    provider_config_hash="b" * 64,
                )
            await db.rollback()
            after_count = (
                await db.execute(select(func.count()).select_from(ResearchRun))
            ).scalar_one()
            self.assertEqual(before_count, after_count)

    async def test_deferred_action_cardinality_rejects_incomplete_plan(self):
        suffix = uuid.uuid4().hex
        async with async_session_maker() as db:
            pool = SourcePool(
                key=f"research-cardinality-{suffix}",
                name="Research cardinality pool",
                topic="migration invariant",
            )
            db.add(pool)
            await db.flush()
            run = ResearchRun(
                source_pool_id=pool.id,
                title="Incomplete plan",
                objective="Verify that missing tool actions cannot be committed.",
                constraints={},
                actor_label="local-user-self-attested",
            )
            db.add(run)
            await db.flush()
            manifest = build_research_input_manifest(
                inventory={},
                provider_name="fake-provider",
                model_name="fake-model-v1",
                provider_config_hash="b" * 64,
            )
            db.add(
                ResearchPlan(
                    run_id=run.id,
                    provider="fake-provider",
                    model="fake-model-v1",
                    prompt_version=RESEARCH_PLAN_PROMPT_VERSION,
                    system_prompt_sha256="0" * 64,
                    input_hash=sha256_json(manifest),
                    input_manifest=manifest,
                    output_hash=sha256_json({}),
                    plan={},
                    action_count=1,
                    model_metadata={},
                )
            )
            with self.assertRaises(DBAPIError):
                await db.commit()
            await db.rollback()

    async def test_interpretation_database_guards_are_installed(self):
        expected = {
            "trg_evidence_interpretations_immutable",
            "trg_evidence_interpretations_immutable_truncate",
            "trg_evidence_interpretation_inputs_immutable",
            "trg_evidence_interpretation_inputs_immutable_truncate",
            "trg_evidence_interpretation_input_set",
            "trg_evidence_interpretation_input_row",
        }
        async with async_session_maker() as db:
            rows = (
                await db.execute(
                    text(
                        "SELECT tgname FROM pg_trigger "
                        "WHERE NOT tgisinternal AND tgname = ANY(:names)"
                    ),
                    {"names": list(expected)},
                )
            ).scalars().all()
        self.assertEqual(set(rows), expected)


if __name__ == "__main__":
    unittest.main()
