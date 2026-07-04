
import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def fix_database():
    print("🛠️ 正在修复数据库列缺失问题...")
    async with async_engine.connect() as conn:
        try:
            # 1. 尝试添加 target_panel_ids 到 raw_intelligence
            print("➡️ 正在向 raw_intelligence 添加 target_panel_ids 列...")
            await conn.execute(text("ALTER TABLE raw_intelligence ADD COLUMN IF NOT EXISTS target_panel_ids JSONB DEFAULT '[]'::jsonb;"))
            
            # 2. 顺便检查 structured_signals 是否也缺这个字段 (虽然目前没报错，但模型里有)
            print("➡️ 正在向 structured_signals 添加 target_panel_ids 列...")
            await conn.execute(text("ALTER TABLE structured_signals ADD COLUMN IF NOT EXISTS target_panel_ids JSONB DEFAULT '[]'::jsonb;"))
            
            await conn.commit()
            print("✅ 数据库修复成功！")
        except Exception as e:
            print(f"❌ 修复失败: {e}")
            await conn.rollback()

if __name__ == "__main__":
    asyncio.run(fix_database())
