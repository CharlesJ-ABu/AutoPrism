import asyncio
from app.core.database import async_engine, Base
from app.models.sql import RawIntelligence, StructuredSignal

async def reset_schema():
    print("Dropping tables...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Schema reset successfully.")

if __name__ == "__main__":
    asyncio.run(reset_schema())
