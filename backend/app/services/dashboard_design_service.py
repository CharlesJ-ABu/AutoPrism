from __future__ import annotations

from typing import Any

from app.ai.providers import StructuredModelProvider
from app.domain.panel_schema import validate_panel_schema


DASHBOARD_PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "panels": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "data_schema": {"type": "object"},
                    "visualization_contract": {"type": "object"},
                    "ui_dsl": {"type": "object"},
                    "extraction_prompt": {"type": "string"},
                    "source_discovery_query": {"type": "string"},
                },
                "required": [
                    "key",
                    "title",
                    "description",
                    "data_schema",
                    "visualization_contract",
                    "ui_dsl",
                    "extraction_prompt",
                    "source_discovery_query",
                ],
            },
        },
    },
    "required": ["title", "description", "panels"],
}


class DashboardDesignService:
    def __init__(self, provider: StructuredModelProvider):
        self.provider = provider

    async def propose(self, title: str) -> dict[str, Any]:
        response = await self.provider.generate(
            system_prompt=(
                "Design an evidence-driven research dashboard. Use only safe UI DSL "
                "components: metric, table, ticker, bar, line, area, radar, heatmap, "
                "timeline, map, network. Every panel needs a strict JSON Schema with "
                "x-autoprism time_dimension, geographic_dimension, aggregation, and "
                "visualization_mapping. Numeric fields require x-unit or x-unitless."
            ),
            user_prompt=f"Design a complete dashboard for this research topic: {title}",
            output_schema=DASHBOARD_PROPOSAL_SCHEMA,
        )
        proposal = response.data
        errors: list[dict[str, str]] = []
        for index, panel in enumerate(proposal.get("panels", [])):
            for issue in validate_panel_schema(panel.get("data_schema", {})):
                errors.append(
                    {
                        "path": f"$.panels[{index}]{issue.path[1:]}",
                        "message": issue.message,
                    }
                )
        if errors:
            raise ValueError({"message": "invalid dashboard proposal", "issues": errors})
        proposal["_generation"] = {
            "provider": response.provider,
            "model": response.model,
            "metadata": response.raw_metadata,
        }
        return proposal
