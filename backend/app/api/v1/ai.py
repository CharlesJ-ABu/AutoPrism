from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.services.ai_service import AIService
from app.models.sql import StrategicInsight
from pydantic import BaseModel
from typing import List

router = APIRouter()

class DenoiseRequest(BaseModel):
    role: str

@router.post("/denoise")
async def trigger_denoise(request: DenoiseRequest, db: AsyncSession = Depends(get_db)):
    """
    触发基于角色的 AI 降噪与战略洞察生成
    """
    ai_service = AIService(db)
    success = await ai_service.generate_strategic_insight(request.role)
    
    if not success:
        raise HTTPException(status_code=500, detail="Strategic insight generation failed or no data available")
    
    return {"status": "success", "message": f"Strategic insights for {request.role} generated."}

@router.get("/insights")
async def get_strategic_insights(role: str = "全量情报", db: AsyncSession = Depends(get_db)):
    """
    获取 L2 库中的战略洞察结果
    """
    print(f"--- [DEBUG] Fetching insights for role: '{role}' ---")
    stmt = select(StrategicInsight)
    if role and role != "全量情报":
        stmt = stmt.where(StrategicInsight.role == role)
    
    result = await db.execute(stmt.order_by(desc(StrategicInsight.created_at)).limit(50))
    items = result.scalars().all()
    print(f"--- [DEBUG] Found {len(items)} insights ---")
    return items
