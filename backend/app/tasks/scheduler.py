# AutoPrism - Scheduled Tasks
from datetime import datetime, timezone
from app.core.database import async_session_maker
from app.services.crawler_service import CrawlerService

async def cleanup_expired_cache():
    """清理过期数据"""
    print(f"[Scheduler] Cleanup check at {datetime.now(timezone.utc)}")

async def refresh_all_sources():
    """
    全网情报抓取任务。
    """
    from app.api.v1.ws import manager
    await manager.broadcast({"type": "log", "message": "DEBUG: 后端任务进程已启动...", "level": "info"})
    
    print(f"[Scheduler] Start Global Intelligence Fetch at {datetime.now(timezone.utc)}")
    async with async_session_maker() as db:
        service = CrawlerService(db)
        count = await service.run_global_sync()
        print(f"[Scheduler] Fetch complete. {count} sources processed.")

async def update_tag_hotness():
    """标签热度计算 (AutoPrism 暂不使用)"""
    pass
