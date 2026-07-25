from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.core.database import get_db
from app.models.sql import IntelligenceInfo, IntelligenceInfoEvidence, RawIntelligence

router = APIRouter()

@router.get("/")
async def get_all_signals(
    limit: int | None = Query(default=None, ge=1, le=1000),
    per_panel_limit: int = Query(default=15, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有 INFO 数据库中的结构化情报信息，带来源信息。
    """
    # 27 个核心面板 ID 集合
    PANELS = [
        "p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9",
        "p13", "p14", "p15", "p16", "p17", "p18", "p21", "p22",
        "p23", "p24", "p25", "p26", "p27", "p28", "p29", "p30",
        "p31", "p32"
    ]
    
    output = []
    seen_ids = set()

    for pid in PANELS:
        stmt = (
            select(
                IntelligenceInfo,
                RawIntelligence.source_name,
                RawIntelligence.source_url,
                RawIntelligence.raw_content,
                RawIntelligence.verification_status,
                RawIntelligence.content_hash,
                RawIntelligence.revision,
                RawIntelligence.fetched_at,
            )
            .join(RawIntelligence, IntelligenceInfo.raw_id == RawIntelligence.id)
            .where(IntelligenceInfo.target_panel_ids.contains([pid]))
            .order_by(IntelligenceInfo.created_at.desc())
            .limit(per_panel_limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        for (
            info,
            source_name,
            source_url,
            raw_content,
            verification_status,
            content_hash,
            revision,
            fetched_at,
        ) in rows:
            if info.id not in seen_ids:
                seen_ids.add(info.id)
                output.append({
                    "id": str(info.id),
                    "title": info.title_brief,
                    "source_name": source_name, 
                    "source_url": source_url,
                    "verification_status": verification_status,
                    "content_hash": content_hash,
                    "revision": revision,
                    "fetched_at": fetched_at.isoformat() if fetched_at else None,
                    "content": raw_content,
                    "summary": [], # Info 表暂不存冗余 summary
                    "geolocation": info.geolocation, 
                    "impact_score": info.impact_score,
                    "sentiment": info.sentiment,
                    "target_panel_ids": info.target_panel_ids,
                    "metrics": info.metrics,
                    "evidence": [],
                    "created_at": info.created_at.isoformat() if info.created_at else None
                })
                
    # 按照时间整体重新倒序，确保前台看到的是最新的
    output.sort(key=lambda x: x["created_at"] or "", reverse=True)
    if limit is not None:
        output = output[:limit]

    # 一次读取当前响应所需的全部证据，避免每条 INFO 单独查询。
    output_ids = [UUID(item["id"]) for item in output]
    if output_ids:
        evidence_stmt = (
            select(
                IntelligenceInfoEvidence.info_id,
                RawIntelligence,
                IntelligenceInfoEvidence.locator,
                IntelligenceInfoEvidence.excerpt,
            )
            .join(
                RawIntelligence,
                IntelligenceInfoEvidence.raw_id == RawIntelligence.id,
            )
            .where(IntelligenceInfoEvidence.info_id.in_(output_ids))
            .order_by(RawIntelligence.created_at.asc())
        )
        evidence_by_info: dict[str, list[dict]] = {}
        for info_id, raw, locator, excerpt in (await db.execute(evidence_stmt)).all():
            evidence_by_info.setdefault(str(info_id), []).append({
                "raw_id": str(raw.id),
                "source_name": raw.source_name,
                "source_url": raw.source_url,
                "content_hash": raw.content_hash,
                "verification_status": raw.verification_status,
                "revision": raw.revision,
                "fetched_at": raw.fetched_at.isoformat() if raw.fetched_at else None,
                "locator": locator,
                "excerpt": excerpt,
            })
        for item in output:
            item["evidence"] = evidence_by_info.get(item["id"], [])

    return output
