from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.ai.providers import DeterministicMappingProvider
from app.core.database import async_session_maker
from app.models.dashboards import (
    Dashboard,
    DashboardVersion,
    PanelDefinition,
    PanelVersion,
    TemplateKind,
    VersionState,
)
from app.models.sources import CollectionJob, SourceDefinition, SourceKind, SourcePool
from app.services.collection_service import CollectionService
from app.services.extraction_service import ExtractionService


@dataclass(frozen=True)
class PanelSeed:
    key: str
    title: str
    description: str
    source_key: str
    source_name: str
    source_url: str
    count_field: str
    results_field: str
    item_schema: dict
    table_columns: list[str]


PANELS = (
    PanelSeed(
        key="us-vehicle-makes",
        title="美国车辆品牌登记概览",
        description="NHTSA vPIC 官方品牌登记总数及原始品牌目录。",
        source_key="nhtsa-vpic-all-makes",
        source_name="NHTSA vPIC — All Makes",
        source_url="https://vpic.nhtsa.dot.gov/api/vehicles/getallmakes?format=json",
        count_field="Count",
        results_field="Results",
        item_schema={
            "type": "object",
            "properties": {
                "Make_ID": {"type": "integer"},
                "Make_Name": {"type": "string"},
            },
            "required": ["Make_ID", "Make_Name"],
        },
        table_columns=["Make_ID", "Make_Name"],
    ),
    PanelSeed(
        key="tesla-2024-models",
        title="Tesla 2024 车型目录",
        description="NHTSA vPIC 官方 2024 年 Tesla 车型清单。",
        source_key="nhtsa-vpic-tesla-2024",
        source_name="NHTSA vPIC — Tesla Models, MY2024",
        source_url=(
            "https://vpic.nhtsa.dot.gov/api/vehicles/"
            "GetModelsForMakeYear/make/tesla/modelyear/2024?format=json"
        ),
        count_field="Count",
        results_field="Results",
        item_schema={
            "type": "object",
            "properties": {
                "Make_ID": {"type": "integer"},
                "Make_Name": {"type": "string"},
                "Model_ID": {"type": "integer"},
                "Model_Name": {"type": "string"},
            },
            "required": ["Make_ID", "Make_Name", "Model_ID", "Model_Name"],
        },
        table_columns=["Make_Name", "Model_Name", "Model_ID"],
    ),
    PanelSeed(
        key="tesla-model3-2024-safety-ratings",
        title="Tesla Model 3 2024 安全评级车型",
        description="NHTSA 5-Star Safety Ratings 官方可评级车型记录。",
        source_key="nhtsa-safety-ratings-model3-2024",
        source_name="NHTSA Safety Ratings — Tesla Model 3, MY2024",
        source_url=(
            "https://api.nhtsa.gov/SafetyRatings/modelyear/2024/"
            "make/Tesla/model/Model%203?format=json"
        ),
        count_field="Count",
        results_field="Results",
        item_schema={
            "type": "object",
            "properties": {
                "VehicleDescription": {"type": "string"},
                "VehicleId": {"type": "integer"},
            },
            "required": ["VehicleDescription", "VehicleId"],
        },
        table_columns=["VehicleDescription", "VehicleId"],
    ),
)


def _schema(panel: PanelSeed) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "record_count": {
                "type": "integer",
                "minimum": 0,
                "x-unit": "record",
            },
            "records": {
                "type": "array",
                "items": panel.item_schema,
            },
        },
        "required": ["record_count", "records"],
        "additionalProperties": False,
        "x-autoprism": {
            "time_dimension": "snapshot.retrieved_at",
            "geographic_dimension": "US",
            "aggregation": {"record_count": "latest_snapshot"},
            "visualization_mapping": {
                "metric": "record_count",
                "table": "records",
            },
        },
    }


def _ui_dsl(panel: PanelSeed) -> dict:
    return {
        "version": "1",
        "type": "stack",
        "children": [
            {
                "type": "metric",
                "field": "record_count",
                "label": "官方记录数",
                "unit": "record",
            },
            {
                "type": "table",
                "field": "records",
                "columns": panel.table_columns,
                "page_size": 20,
            },
            {
                "type": "provenance",
                "show_source": True,
                "show_retrieved_at": True,
                "show_artifact_hash": True,
                "show_locator": True,
            },
        ],
    }


async def seed(*, collect: bool) -> dict:
    async with async_session_maker() as db:
        pool = (
            await db.execute(
                select(SourcePool).where(SourcePool.key == "official-us-automotive")
            )
        ).scalar_one_or_none()
        if pool is None:
            pool = SourcePool(
                key="official-us-automotive",
                name="美国官方汽车数据源池",
                topic="Automotive safety, makes, models and ratings",
                discovery_query="site:nhtsa.gov vehicle API data",
                settings={
                    "authority": "US Department of Transportation / NHTSA",
                    "usage_basis": "official public API",
                    "policy": {
                        "respect_terms": True,
                        "respect_robots": True,
                        "rate_limit": "sequential manual seed",
                    },
                },
            )
            db.add(pool)
            await db.flush()

        dashboard = (
            await db.execute(
                select(Dashboard).where(Dashboard.key == "automotive-official-demo")
            )
        ).scalar_one_or_none()
        if dashboard is None:
            dashboard = Dashboard(
                key="automotive-official-demo",
                title="汽车官方数据审计面板",
                description="三个 NHTSA 官方 API 的真实、可回放 V2 面板。",
            )
            db.add(dashboard)
            await db.flush()

        version = (
            await db.execute(
                select(DashboardVersion).where(
                    DashboardVersion.dashboard_id == dashboard.id,
                    DashboardVersion.version == 1,
                )
            )
        ).scalar_one_or_none()
        if version is None:
            version = DashboardVersion(
                dashboard_id=dashboard.id,
                version=1,
                state=VersionState.PUBLISHED,
                research_brief={
                    "scope": "official NHTSA API demonstrator",
                    "evidence_policy": "raw snapshot + JSON Pointer + SHA-256",
                },
                generation_model="human-reviewed-seed",
                generation_prompt_version="v2-reference-1",
            )
            db.add(version)
            await db.flush()

        pairs: list[tuple[SourceDefinition, PanelVersion]] = []
        for panel in PANELS:
            source = (
                await db.execute(
                    select(SourceDefinition).where(
                        SourceDefinition.pool_id == pool.id,
                        SourceDefinition.key == panel.source_key,
                    )
                )
            ).scalar_one_or_none()
            if source is None:
                source = SourceDefinition(
                    pool_id=pool.id,
                    key=panel.source_key,
                    name=panel.source_name,
                    canonical_url=panel.source_url,
                    kind=SourceKind.API,
                    global_reputation=1,
                    topic_authority=1,
                    refresh_policy={"mode": "manual", "recommended_hours": 24},
                    request_config={
                        "timeout_seconds": 60,
                        "max_bytes": 25 * 1024 * 1024,
                        "publisher_identity": "nhtsa",
                    },
                    parser_config={},
                )
                db.add(source)
                await db.flush()

            definition = (
                await db.execute(
                    select(PanelDefinition).where(
                        PanelDefinition.dashboard_id == dashboard.id,
                        PanelDefinition.key == panel.key,
                    )
                )
            ).scalar_one_or_none()
            if definition is None:
                definition = PanelDefinition(
                    dashboard_id=dashboard.id,
                    key=panel.key,
                )
                db.add(definition)
                await db.flush()
            panel_version = (
                await db.execute(
                    select(PanelVersion).where(
                        PanelVersion.panel_id == definition.id,
                        PanelVersion.version == 1,
                    )
                )
            ).scalar_one_or_none()
            if panel_version is None:
                panel_version = PanelVersion(
                    panel_id=definition.id,
                    dashboard_version_id=version.id,
                    version=1,
                    title=panel.title,
                    description=panel.description,
                    data_schema=_schema(panel),
                    template_kind=TemplateKind.UI_DSL,
                    ui_dsl=_ui_dsl(panel),
                    visualization_contract=_ui_dsl(panel),
                    extraction_prompt="Use the frozen JSON mapping only.",
                    extraction_prompt_version="json-mapping-v1",
                    model_settings={
                        "extraction_engine": "json_mapping_v1",
                        "field_mappings": {
                            "record_count": {
                                "path": panel.count_field,
                                "transform": "integer",
                            },
                            "records": panel.results_field,
                        },
                    },
                    source_pool_id=pool.id,
                )
                db.add(panel_version)
                await db.flush()
            pairs.append((source, panel_version))
        await db.commit()

        results = []
        if collect:
            for source, panel_version in pairs:
                job = CollectionJob(
                    source_definition_id=source.id,
                    idempotency_key=f"reference:{source.key}:{uuid.uuid4()}",
                )
                db.add(job)
                await db.commit()
                completed = await CollectionService(db).run_job(job.id)
                item = {
                    "source": source.key,
                    "job_id": str(completed.id),
                    "state": completed.state.value,
                }
                if completed.result_snapshot_id:
                    extraction = await ExtractionService(
                        db,
                        DeterministicMappingProvider(panel_version.model_settings),
                    ).extract(
                        panel_version_id=panel_version.id,
                        snapshot_id=completed.result_snapshot_id,
                    )
                    item.update(
                        {
                            "snapshot_id": str(completed.result_snapshot_id),
                            "extraction_run_id": str(extraction.run_id),
                            "observation_ids": [
                                str(value) for value in extraction.observation_ids
                            ],
                            "issues": [
                                {"path": issue.path, "message": issue.message}
                                for issue in extraction.issues
                            ],
                        }
                    )
                else:
                    item["error"] = completed.error
                results.append(item)
        return {
            "dashboard_id": str(dashboard.id),
            "dashboard_version_id": str(version.id),
            "source_pool_id": str(pool.id),
            "panels": results if collect else [panel.key for panel in PANELS],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collect",
        action="store_true",
        help="fetch the three official APIs and run deterministic extraction",
    )
    arguments = parser.parse_args()
    print(json.dumps(asyncio.run(seed(collect=arguments.collect)), indent=2))


if __name__ == "__main__":
    main()
