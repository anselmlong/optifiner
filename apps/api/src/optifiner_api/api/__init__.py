"""API routes module."""

from fastapi import APIRouter

from optifiner_api.api.optimization import router as optimization_router
from optifiner_api.api.early_access import router as early_access_router

# Create main router
router = APIRouter()

router.include_router(optimization_router, tags=["optimization"])
router.include_router(early_access_router, tags=["early-access"])
