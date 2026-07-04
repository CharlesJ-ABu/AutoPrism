# Tech Nebula - Main Application
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.api.v1 import router as api_v1_router
from app.api.v1.websocket import router as ws_router
from app.core.config import settings
from app.core.database import async_engine, Base
from app.tasks.scheduler import cleanup_expired_cache, refresh_all_sources, update_tag_hotness


from app.api.v1.system import apply_scheduler_config
from app.core.state import system_state

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Attach scheduler to app state so API endpoints can reach it
    app.state.scheduler = scheduler

    # Start scheduler
    scheduler.add_job(cleanup_expired_cache, CronTrigger(hour=8, minute=0), id="cleanup")
    scheduler.add_job(update_tag_hotness, CronTrigger(hour=8, minute=0), id="hotness")

    # Initialize crawler & AI jobs from global state
    apply_scheduler_config(scheduler, system_state.config)

    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
