"""Task management API endpoints."""

from fastapi import APIRouter, HTTPException

from optifiner_api.models import TaskSubmitRequest
from optifiner_api.services.worker_service import WorkerService

router = APIRouter()

# Initialize service
worker_service = WorkerService()


@router.post("/tasks/submit")
async def submit_task(request: TaskSubmitRequest):
    """Submit a task to the worker.

    Args:
        request: Task submission request

    Returns:
        Task submission result
    """
    result = await worker_service.submit_task(
        repo_dir=request.repo_dir,
        agent_type=request.agent_type,
        task_prompt=request.task_prompt,
        model=request.model,
        max_iterations=request.max_iterations,
        metrics=request.metrics,
        baseline=request.baseline,
        analysis=request.analysis,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Task submission failed")
        )

    return result


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status.

    Args:
        task_id: Task identifier

    Returns:
        Task status
    """
    result = await worker_service.get_task_status(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Task not found")
        )

    return result


@router.get("/tasks")
async def list_tasks(limit: int = 50):
    """List recent tasks.

    Args:
        limit: Maximum number of tasks to return

    Returns:
        List of tasks
    """
    tasks = await worker_service.list_tasks(limit=limit)
    return {"tasks": tasks}
