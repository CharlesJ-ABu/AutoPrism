from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.domain.evidence import sha256_json


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    api_key: str
    base_url: str
    timeout_seconds: float = 120


@dataclass(frozen=True)
class StructuredModelResponse:
    data: dict[str, Any]
    provider: str
    model: str
    raw_metadata: dict[str, Any]


class StructuredModelProvider(Protocol):
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> StructuredModelResponse: ...


def _read_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split(".") if path else ():
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(path)
    return current


class DeterministicMappingProvider:
    """Map frozen JSON source fields without letting a model invent values."""

    def __init__(self, mapping: dict[str, Any]):
        self.mapping = mapping

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> StructuredModelResponse:
        marker = "Evidence fragments:\n"
        if marker not in user_prompt:
            raise ValueError("evidence context is missing")
        fragments = json.loads(user_prompt.split(marker, 1)[1])
        records = []
        for fragment in fragments:
            source_value = json.loads(fragment["text"])
            data: dict[str, Any] = {}
            evidence: dict[str, str] = {}
            for output_key, specification in self.mapping.get(
                "field_mappings", {}
            ).items():
                if isinstance(specification, str):
                    specification = {"path": specification}
                value = _read_path(source_value, specification["path"])
                transform = specification.get("transform")
                if transform == "integer":
                    value = int(value)
                elif transform == "number":
                    value = float(value)
                elif transform == "string":
                    value = str(value)
                data[output_key] = value
                evidence[output_key] = fragment["evidence_fragment_id"]
            for output_key, value in self.mapping.get("constants", {}).items():
                data[output_key] = value
                evidence[output_key] = fragment["evidence_fragment_id"]
            records.append({"data": data, "evidence": evidence})
        return StructuredModelResponse(
            data={"records": records},
            provider="deterministic",
            model="json-mapping-v1",
            raw_metadata={
                "mapping_hash": sha256_json(self.mapping),
                "record_count": len(records),
            },
        )


class OpenAICompatibleProvider:
    def __init__(self, config: ModelConfig):
        self.config = config

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> StructuredModelResponse:
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                json={
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            return StructuredModelResponse(
                data=json.loads(content),
                provider=self.config.provider,
                model=self.config.model,
                raw_metadata={
                    "id": body.get("id"),
                    "usage": body.get("usage", {}),
                },
            )


class GeminiProvider:
    def __init__(self, config: ModelConfig):
        self.config = config

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
    ) -> StructuredModelResponse:
        url = (
            f"{self.config.base_url.rstrip('/')}/models/"
            f"{self.config.model}:generateContent"
        )
        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                url,
                params={"key": self.config.api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "temperature": 0,
                        "responseMimeType": "application/json",
                        "responseJsonSchema": output_schema,
                    },
                },
            )
            response.raise_for_status()
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            return StructuredModelResponse(
                data=json.loads(text),
                provider=self.config.provider,
                model=self.config.model,
                raw_metadata={"usage": body.get("usageMetadata", {})},
            )


def create_provider(config: ModelConfig) -> StructuredModelProvider:
    normalized = config.provider.lower()
    if normalized in {"openai", "openai-compatible", "compatible"}:
        return OpenAICompatibleProvider(config)
    if normalized in {"gemini", "google"}:
        return GeminiProvider(config)
    raise ValueError(f"unsupported model provider: {config.provider}")
