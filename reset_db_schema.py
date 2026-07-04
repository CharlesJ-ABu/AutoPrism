import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

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
