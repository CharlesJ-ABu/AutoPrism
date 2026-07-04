from fastapi import APIRouter
from app.api.v1.signals import router as signals_router
from app.api.v1.system import router as system_router
from app.api.v1.ai import router as ai_router

router = APIRouter()

router.include_router(signals_router, prefix="/intel", tags=["Intelligence"])
router.include_router(system_router, prefix="/admin", tags=["System Control"])
router.include_router(ai_router, prefix="/ai", tags=["AI Strategy"])
