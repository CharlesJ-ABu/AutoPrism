from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.v2 import router as api_v2_router
from app.core.config import settings
from app.core.database import Base, async_engine, async_session_maker
from app.models import dashboards as _dashboard_models  # noqa: F401
from app.models import evidence as _evidence_models  # noqa: F401
from app.models import sources as _source_models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.V2_AUTO_CREATE_SCHEMA:
        async with async_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_v2_router, prefix="/api/v2")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/ready")
async def readiness_check():
    async with async_session_maker() as session:
        await session.execute(text("SELECT 1"))
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis.ping()
    finally:
        await redis.aclose()
    return {"status": "ready", "database": "ok", "redis": "ok"}


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "api": "/api/v2",
        "docs": "/docs",
    }
