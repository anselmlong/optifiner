"""API routes module."""

from fastapi import APIRouter

from optifiner_api.api.optimization import router as optimization_router

# Create main router
router = APIRouter()

router.include_router(optimization_router, tags=["optimization"])
