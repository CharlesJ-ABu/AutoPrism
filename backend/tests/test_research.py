import os
import unittest
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.ai.providers import StructuredModelResponse
from app.core.database import async_engine, async_session_maker
from app.domain.evidence import canonical_json, sha256_json
from app.models.research import (
    ResearchAction,
    ResearchActionEvent,
    ResearchEventType,
    ResearchPlan,
    ResearchRun,
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


if __name__ == "__main__":
    unittest.main()
