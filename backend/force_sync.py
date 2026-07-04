import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.sql import Base, RawIntelligence, IntelligenceStatus, StructuredSignal
from app.services.crawler_service import CrawlerService
from app.services.ai_service import AIService
from app.core.config import settings

async def force_sync():
    print("🚀 正在启动底层强制同步引擎...")
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. 强制采集东方财富数据
        crawler = CrawlerService(db)
        print("🔍 正在抓取东方财富全球宏观指标...")
        new_count = await crawler.fetch_all()
        print(f"✅ 抓取完成，入库 {new_count} 条原始情报。")
        
        # 2. 强制执行 AI 结构化
        ai = AIService(db)
        print("🧠 正在启动 AI 结构化降噪管线...")
        processed_count = await ai.process_pending_intelligence(limit=20)
        print(f"📊 AI 解析完成，生成 {processed_count} 条结构化信号。")
        
        await db.commit()
    
    print("\n✨ 任务圆满完成！请刷新浏览器查看面板。")

if __name__ == "__main__":
    asyncio.run(force_sync())
