from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.sql import IntelligenceInfo, RawIntelligence

router = APIRouter()

@router.get("/")
async def get_all_signals(db: AsyncSession = Depends(get_db)):
    """
    获取所有 INFO 数据库中的结构化情报信息，带来源信息。
    """
    # 联表查询 IntelligenceInfo 和 RawIntelligence
    stmt = (
        select(IntelligenceInfo, RawIntelligence.source_name, RawIntelligence.source_url, RawIntelligence.raw_content)
        .join(RawIntelligence, IntelligenceInfo.raw_id == RawIntelligence.id)
        .order_by(IntelligenceInfo.created_at.desc())
        .limit(200) # 调大限制，因为 27 个面板需要更多数据
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    # 转换为前端大屏需要的标准格式
    output = []
    for info, source_name, source_url, raw_content in rows:
        output.append({
            "id": str(info.id),
            "title": info.title_brief,
            "source_name": source_name, 
            "source_url": source_url,
            "content": raw_content,
            "summary": [], # Info 表暂不存冗余 summary
            "geolocation": info.geolocation, 
            "impact_score": info.impact_score,
            "sentiment": info.sentiment,
            "target_panel_ids": info.target_panel_ids,
            "metrics": info.metrics,
            "created_at": info.created_at.isoformat() if info.created_at else None
        })
    return output
