import asyncio
from sqlalchemy import text
from app.core.database import async_engine, Base
from app.models.sql import StrategicInsight

async def reset_l2():
    print("🚀 正在重置 L2 战略洞察表以应用最新 Schema (geo_coordinates)...")
    async with async_engine.begin() as conn:
        # 仅删除战略洞察表，不影响原始数据和面板数据
        await conn.execute(text("DROP TABLE IF EXISTS strategic_insights CASCADE"))
        # 重新创建
        await conn.run_sync(Base.metadata.create_all)
    print("✅ L2 表重置成功！")

if __name__ == "__main__":
    asyncio.run(reset_l2())
