import json
import unittest

import httpx

from app.ai.providers import (
    DeterministicMappingProvider,
    GeminiProvider,
    ModelConfig,
    OpenAICompatibleProvider,
    create_provider,
)


class ModelProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_mapping_provider_cites_source_fragment(self):
        provider = DeterministicMappingProvider(
            {
                "field_mappings": {
                    "vehicle_count": {
                        "path": "Count",
                        "transform": "integer",
                    },
                    "vehicles": "Results",
                }
            }
        )
        response = await provider.generate(
            system_prompt="",
            user_prompt=(
                'Evidence fragments:\n[{"evidence_fragment_id":"fragment-1",'
                '"text":"{\\"Count\\":2,\\"Results\\":[{\\"name\\":\\"A\\"}]}"}]'
            ),
            output_schema={},
        )
        record = response.data["records"][0]
        self.assertEqual(record["data"]["vehicle_count"], 2)
        self.assertEqual(record["evidence"]["vehicles"], "fragment-1")
        self.assertEqual(response.provider, "deterministic")

    async def test_deterministic_mapping_rejects_constants(self):
        with self.assertRaisesRegex(ValueError, "constants are forbidden"):
            DeterministicMappingProvider(
                {
                    "field_mappings": {"revenue": "reported_revenue"},
                    "constants": {"revenue": 999},
                }
            )

    async def test_deterministic_mapping_does_not_coerce_values(self):
        provider = DeterministicMappingProvider(
            {
                "field_mappings": {
                    "vehicle_count": {
                        "path": "Count",
                        "transform": "integer",
                    }
                }
            }
        )
        with self.assertRaisesRegex(ValueError, "not already an integer"):
            await provider.generate(
                system_prompt="",
                user_prompt=(
                    'Evidence fragments:\n[{"evidence_fragment_id":"fragment-1",'
                    '"text":"{\\"Count\\":\\"2\\"}"}]'
                ),
                output_schema={},
            )

    async def test_deterministic_mapping_rejects_unavailable_source_paths(self):
        for path in ("missing", "Results.3", "Results.not-an-index"):
            with self.subTest(path=path):
                provider = DeterministicMappingProvider(
                    {"field_mappings": {"value": path}}
                )
                with self.assertRaisesRegex(ValueError, "source path"):
                    await provider.generate(
                        system_prompt="",
                        user_prompt=(
                            'Evidence fragments:\n'
                            '[{"evidence_fragment_id":"fragment-1",'
                            '"text":"{\\"Results\\":[1]}"}]'
                        ),
                        output_schema={},
                    )

    async def test_openai_compatible_adapter(self):
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "id": "response-1",
                    "choices": [{"message": {"content": json.dumps({"records": []})}}],
                    "usage": {"total_tokens": 3},
                },
                request=request,
            )
        )
        original_client = httpx.AsyncClient

        class MockClient(httpx.AsyncClient):
            def __init__(self, *args, **kwargs):
                super().__init__(transport=transport)

        httpx.AsyncClient = MockClient
        try:
            provider = OpenAICompatibleProvider(
                ModelConfig("openai-compatible", "model", "secret", "https://api.test/v1")
            )
            response = await provider.generate(
                system_prompt="system",
                user_prompt="user",
                output_schema={"type": "object"},
            )
            self.assertEqual(response.data, {"records": []})
            self.assertEqual(response.raw_metadata["usage"]["total_tokens"], 3)
        finally:
            httpx.AsyncClient = original_client

    def test_registry_is_provider_neutral(self):
        gemini = create_provider(
            ModelConfig("gemini", "gemini-test", "secret", "https://google.test/v1beta")
        )
        self.assertIsInstance(gemini, GeminiProvider)
        with self.assertRaises(ValueError):
            create_provider(ModelConfig("unknown", "m", "k", "https://example.test"))


if __name__ == "__main__":
    unittest.main()
