from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

import httpx
import simplejson as json

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
            if part not in current:
                raise ValueError(f"source path {path!r} is unavailable")
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit():
                raise ValueError(f"source path {path!r} has an invalid array index")
            index = int(part)
            if index >= len(current):
                raise ValueError(f"source path {path!r} is unavailable")
            current = current[index]
        else:
            raise ValueError(f"source path {path!r} is unavailable")
    return current


class DeterministicMappingProvider:
    """Map frozen JSON source fields without letting a model invent values."""

    def __init__(self, mapping: dict[str, Any]):
        validate_deterministic_mapping(mapping)
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
        fragments = json.loads(user_prompt.split(marker, 1)[1], use_decimal=True)
        records = []
        for fragment in fragments:
            source_value = json.loads(fragment["text"], use_decimal=True)
            data: dict[str, Any] = {}
            evidence: dict[str, str] = {}
            for output_key, specification in self.mapping.get(
                "field_mappings", {}
            ).items():
                if isinstance(specification, str):
                    specification = {"path": specification}
                value = _read_path(source_value, specification["path"])
                transform = specification.get("transform")
                if transform == "integer" and (
                    isinstance(value, bool) or not isinstance(value, int)
                ):
                    raise ValueError(
                        f"field {output_key!r} is not already an integer"
                    )
                if transform == "number" and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float, Decimal))
                    or (
                        not value.is_finite()
                        if isinstance(value, Decimal)
                        else not math.isfinite(value)
                    )
                ):
                    raise ValueError(
                        f"field {output_key!r} is not already a finite JSON number"
                    )
                if transform == "string" and not isinstance(value, str):
                    raise ValueError(
                        f"field {output_key!r} is not already a string"
                    )
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


def validate_deterministic_mapping(mapping: dict[str, Any]) -> None:
    """Reject mappings that can synthesize or silently coerce source facts."""

    if not isinstance(mapping, dict):
        raise ValueError("deterministic mapping must be an object")
    if mapping.get("constants"):
        raise ValueError("deterministic extraction constants are forbidden")
    allowed_keys = {"extraction_engine", "field_mappings", "constants"}
    unknown_keys = set(mapping) - allowed_keys
    if unknown_keys:
        raise ValueError(
            "unsupported deterministic mapping settings: "
            + ", ".join(sorted(unknown_keys))
        )
    field_mappings = mapping.get("field_mappings")
    if not isinstance(field_mappings, dict) or not field_mappings:
        raise ValueError("deterministic extraction requires field_mappings")
    for output_key, raw_specification in field_mappings.items():
        if not isinstance(output_key, str) or not output_key:
            raise ValueError("deterministic output keys must be non-empty strings")
        specification = (
            {"path": raw_specification}
            if isinstance(raw_specification, str)
            else raw_specification
        )
        if not isinstance(specification, dict):
            raise ValueError(f"mapping for {output_key!r} must be a path or object")
        if set(specification) - {"path", "transform"}:
            raise ValueError(f"mapping for {output_key!r} has unsupported options")
        if not isinstance(specification.get("path"), str) or not specification["path"]:
            raise ValueError(f"mapping for {output_key!r} requires a source path")
        if specification.get("transform") not in {None, "integer", "number", "string"}:
            raise ValueError(f"mapping for {output_key!r} has unsupported transform")


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
                data=json.loads(content, use_decimal=True),
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
                data=json.loads(text, use_decimal=True),
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
