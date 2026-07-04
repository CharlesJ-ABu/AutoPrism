from fastapi import APIRouter, Request, BackgroundTasks, Depends
from typing import Dict, Any
from app.core.state import system_state
from app.tasks.scheduler import refresh_all_sources
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai_service import AIService
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

router = APIRouter()

def apply_scheduler_config(scheduler, config: Dict[str, Any]):
    """将配置映射到 APScheduler 任务"""

    # --- Crawler Engine ---
    c_mode = config["crawler"]["mode"]
    c_val = config["crawler"]["value"]

    # Clear existing crawler job if any
    if scheduler.get_job("crawler_fetch"):
        scheduler.remove_job("crawler_fetch")

    if c_mode == "daily":
        try:
            hour, minute = map(int, c_val.split(":"))
            scheduler.add_job(refresh_all_sources, CronTrigger(hour=hour, minute=minute), id="crawler_fetch")
        except: pass
    elif c_mode == "interval":
        try:
            scheduler.add_job(refresh_all_sources, IntervalTrigger(minutes=int(c_val)), id="crawler_fetch")
        except: pass
    # Manual mode handles itself by having no job

    # --- AI Denoising Engine ---
    a_mode = config["ai"]["mode"]
    a_val = config["ai"]["value"]

    # Clear existing AI job if any
    if scheduler.get_job("ai_denoise"):
        scheduler.remove_job("ai_denoise")

    if a_mode == "daily":
        try:
            hour, minute = map(int, a_val.split(":"))
            scheduler.add_job(run_ai_pipeline, CronTrigger(hour=hour, minute=minute), id="ai_denoise")
        except: pass
    elif a_mode == "interval":
        try:
            scheduler.add_job(run_ai_pipeline, IntervalTrigger(minutes=int(a_val)), id="ai_denoise")
        except: pass

async def run_ai_pipeline():
    from app.core.database import async_session_maker
    async with async_session_maker() as db:
        service = AIService(db)
        batch_size = system_state.config["ai"]["batch_size"]
        await service.process_pending_intelligence(limit=batch_size)

@router.get("/scheduler/config")
async def get_config():
    return system_state.config

@router.post("/scheduler/config")
async def update_config(payload: Dict[str, Any], request: Request):
    # Map frontend keys to backend keys
    # Frontend: crawlerMode, crawlerValue, aiMode, aiValue
    mapped_config = {
        "crawler": {
            "mode": payload.get("crawlerMode", system_state.config["crawler"]["mode"]),
            "value": payload.get("crawlerValue", system_state.config["crawler"]["value"])
        },
        "ai": {
            "mode": payload.get("aiMode", system_state.config["ai"]["mode"]),
            "value": payload.get("aiValue", system_state.config["ai"]["value"]),
            "batch_size": int(payload.get("aiBatchSize", system_state.config["ai"]["batch_size"]))
        }
    }

    system_state.update_config(mapped_config)
    scheduler = request.app.state.scheduler
    if scheduler:
        apply_scheduler_config(scheduler, system_state.config)
    return {"status": "ok", "config": system_state.config}

@router.post("/trigger/fetch")
async def trigger_fetch(background_tasks: BackgroundTasks):
    async def wrapped_refresh():
        try:
            await refresh_all_sources()
        except Exception as e:
            from app.api.v1.ws import manager
            await manager.broadcast({"type": "log", "message": f"CRITICAL: Crawler failed: {str(e)}", "level": "error"})
            print(f"CRAWLER ERROR: {str(e)}")

    background_tasks.add_task(wrapped_refresh)
    return {"status": "ok", "message": "Intelligence fetch sequence ignited."}

@router.post("/trigger/ai")
async def trigger_ai(background_tasks: BackgroundTasks):
    from app.services.ai_service import AIService
    async def wrapped_ai():
        from app.core.database import async_session_maker
        async with async_session_maker() as db:
            service = AIService(db)
            await service.process_pending_intelligence()

    background_tasks.add_task(wrapped_ai)
    return {"status": "ok", "message": "AI Denoising sequence ignited."}

@router.post("/trigger/panel/{panel_id}")
async def trigger_panel_sync(panel_id: str, background_tasks: BackgroundTasks):
    from app.services.crawler_service import CrawlerService
    async def wrapped_panel_sync():
        from app.core.database import async_session_maker
        async with async_session_maker() as db:
            service = CrawlerService(db)
            await service.run_panel_sync(panel_id)

    background_tasks.add_task(wrapped_panel_sync)
    return {"status": "ok", "message": f"Panel {panel_id} sync sequence ignited."}

@router.get("/debug/raw")
async def get_raw_data(db: AsyncSession = Depends(get_db)):
    """获取第一层原始数据快照 (L1)"""
    from app.models.sql import RawIntelligence
    from sqlalchemy import select, desc
    result = await db.execute(select(RawIntelligence).order_by(desc(RawIntelligence.created_at)).limit(50))
    items = result.scalars().all()
    return [{
        "id": i.id,
        "title": i.title,
        "source": i.source_name,
        "status": i.status,
        "panels": i.target_panel_ids, # 关键：返回 L1 标签
        "created_at": i.created_at
    } for i in items]

@router.get("/debug/info")
async def get_info_snapshot(db: AsyncSession = Depends(get_db)):
    """获取 Info 数据库实时快照 (面板直接来源)"""
    from app.models.sql import IntelligenceInfo
    from sqlalchemy import select, desc
    result = await db.execute(select(IntelligenceInfo).order_by(desc(IntelligenceInfo.created_at)).limit(50))
    items = result.scalars().all()
    return [{
        "id": i.id,
        "title": i.title_brief,
        "panels": i.target_panel_ids,
        "metrics": i.metrics,
        "impact": i.impact_score,
        "created_at": i.created_at
    } for i in items]

@router.get("/debug/structured")
async def get_structured_data(db: AsyncSession = Depends(get_db)):
    """获取 L2 战略洞察数据快照"""
    from app.models.sql import StrategicInsight
    from sqlalchemy import select, desc
    result = await db.execute(select(StrategicInsight).order_by(desc(StrategicInsight.created_at)).limit(50))
    items = result.scalars().all()
    return [{
        "id": str(i.id),
        "title": i.title,
        "summary": i.summary,
        "role": i.role,
        "display_type": i.display_type,
        "geo": i.geo_coordinates,
        "priority": i.priority,
        "sentiment": i.sentiment,
        "panels": i.affected_panels,
        "metrics": i.analysis,
        "advice": i.strategic_advice,
        "created_at": i.created_at
    } for i in items]

@router.post("/trigger/reset/l1")
async def reset_l1(db: AsyncSession = Depends(get_db)):
    """清空 L1 原始情报"""
    from app.models.sql import RawIntelligence
    from sqlalchemy import delete
    from app.api.v1.ws import manager
    await db.execute(delete(RawIntelligence))
    await db.commit()
    await manager.broadcast({"type": "log", "message": "☢️ L1 原始情报库已完全清空。", "level": "error"})
    return {"status": "ok"}

@router.post("/trigger/reset/info")
async def reset_info(db: AsyncSession = Depends(get_db)):
    """清空 INFO 面板解读"""
    from app.models.sql import IntelligenceInfo
    from sqlalchemy import delete
    from app.api.v1.ws import manager
    await db.execute(delete(IntelligenceInfo))
    await db.commit()
    await manager.broadcast({"type": "log", "message": "☢️ INFO 面板解读库已完全清空。", "level": "error"})
    return {"status": "ok"}

@router.post("/trigger/reset/l2")
async def reset_l2(db: AsyncSession = Depends(get_db)):
    """清空 L2 战略洞察"""
    from app.models.sql import StrategicInsight
    from sqlalchemy import delete
    from app.api.v1.ws import manager
    await db.execute(delete(StrategicInsight))
    await db.commit()
    await manager.broadcast({"type": "log", "message": "☢️ L2 战略洞察库已完全清空。", "level": "error"})
    return {"status": "ok"}
