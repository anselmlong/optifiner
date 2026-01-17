"""API routes module."""

from fastapi import APIRouter

from optifiner_api.api.repositories import router as repositories_router
from optifiner_api.api.tasks import router as tasks_router
from optifiner_api.api.evaluations import router as evaluations_router
from optifiner_api.api.workflows import router as workflows_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(repositories_router, tags=["repositories"])
router.include_router(tasks_router, tags=["tasks"])
router.include_router(evaluations_router, tags=["evaluations"])
router.include_router(workflows_router, tags=["workflows"])
