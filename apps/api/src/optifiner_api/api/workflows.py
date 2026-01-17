"""Workflow API endpoints."""

from fastapi import APIRouter, HTTPException

from optifiner_api.services.worker_service import WorkerService

router = APIRouter()

# Initialize service
worker_service = WorkerService()


@router.get("/tasks/{task_id}/workflow")
async def get_task_workflow(task_id: str):
    """Get workflow information for a task.

    This includes agent state, iterations, events, and tool calls.

    Args:
        task_id: Task identifier

    Returns:
        Workflow information
    """
    result = await worker_service.get_workflow_data(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Workflow data not found")
        )

    return result


@router.get("/tasks/{task_id}/workflow/events")
async def get_task_workflow_events(task_id: str):
    """Get workflow events for a task.

    This includes all observability events (agent_start, tool_calls, iterations, etc.).

    Args:
        task_id: Task identifier

    Returns:
        Workflow events
    """
    result = await worker_service.get_workflow_events(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Workflow events not found")
        )

    return result


@router.get("/tasks/{task_id}/workflow/iterations")
async def get_task_workflow_iterations(task_id: str):
    """Get iteration information for a task.

    This includes details about each iteration of the agent workflow.

    Args:
        task_id: Task identifier

    Returns:
        Iteration information
    """
    result = await worker_service.get_workflow_iterations(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Workflow iterations not found")
        )

    return result


@router.get("/tasks/{task_id}/workflow/tools")
async def get_task_workflow_tools(task_id: str):
    """Get tool call history for a task.

    This includes all tool calls made during agent execution with their results.

    Args:
        task_id: Task identifier

    Returns:
        Tool call information
    """
    result = await worker_service.get_workflow_tools(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Workflow tools not found")
        )

    return result


@router.post("/tasks/{task_id}/workflow")
async def store_task_workflow(task_id: str, workflow_data: dict):
    """Store workflow data for a task.

    This endpoint allows workers to store workflow data (events, iterations,
    tool calls, etc.) after task execution.

    Args:
        task_id: Task identifier
        workflow_data: Workflow data dictionary

    Returns:
        Success confirmation
    """
    await worker_service.store_workflow_data(task_id, workflow_data)

    return {
        "success": True,
        "message": f"Workflow data stored for task {task_id}",
        "task_id": task_id,
    }
