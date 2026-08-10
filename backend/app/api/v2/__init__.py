from fastapi import APIRouter

from app.api.v2.evidence import router as evidence_router
from app.api.v2.extractions import router as extractions_router
from app.api.v2.insights import router as insights_router
from app.api.v2.dashboards import router as dashboards_router
from app.api.v2.sources import router as sources_router
from app.api.v2.verification import router as verification_router
from app.api.v2.research import router as research_router


router = APIRouter()
router.include_router(sources_router, prefix="/sources", tags=["V2 Sources"])
router.include_router(evidence_router, prefix="/evidence", tags=["V2 Evidence"])
router.include_router(extractions_router, prefix="/extractions", tags=["V2 Extractions"])
router.include_router(insights_router, prefix="/insights", tags=["V2 Insights"])
router.include_router(dashboards_router, prefix="/dashboards", tags=["V2 Dashboards"])
router.include_router(
    verification_router,
    prefix="/verification",
    tags=["V2 Verification"],
)
router.include_router(research_router, prefix="/research", tags=["V2 Research"])
