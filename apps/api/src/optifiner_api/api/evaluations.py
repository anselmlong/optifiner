"""Evaluation API endpoints."""

from fastapi import APIRouter, HTTPException

from optifiner_api.models import EvaluationDataStoreRequest
from optifiner_api.services.worker_service import WorkerService

router = APIRouter()

# Initialize service
worker_service = WorkerService()


@router.get("/tasks/{task_id}/evaluation")
async def get_evaluation_data(task_id: str):
    """Get evaluation data for a completed task.

    Args:
        task_id: Task identifier

    Returns:
        Evaluation data
    """
    result = await worker_service.get_evaluation_data(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Evaluation data not found")
        )

    return result


@router.get("/tasks/{task_id}/evaluation/summary")
async def get_evaluation_summary(task_id: str):
    """Get a summary of evaluation data for a completed task.

    Args:
        task_id: Task identifier

    Returns:
        Evaluation summary with key metrics
    """
    result = await worker_service.get_evaluation_data(task_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Evaluation data not found")
        )

    eval_data = result.get("evaluation_data", {})
    
    # Extract key metrics for summary
    summary = {
        "task_id": task_id,
        "score": eval_data.get("score"),
        "baseline_score": eval_data.get("baseline_score"),
        "improvement": eval_data.get("improvement"),
        "improvement_percent": eval_data.get("improvement_percent"),
        "fps": eval_data.get("fps"),
        "tests_passed": eval_data.get("tests_passed"),
        "tests_total": eval_data.get("tests_total"),
        "success": eval_data.get("success", False),
    }

    return {"success": True, "summary": summary}


@router.post("/tasks/{task_id}/evaluation")
async def store_evaluation_data(task_id: str, request: EvaluationDataStoreRequest):
    """Store evaluation data for a completed task.

    This endpoint allows workers or external systems to store evaluation data
    after an evaluation is complete.

    Args:
        task_id: Task identifier (must match request.task_id)
        request: Evaluation data store request

    Returns:
        Success confirmation
    """
    if task_id != request.task_id:
        raise HTTPException(
            status_code=400, detail="Task ID in path must match task_id in request body"
        )

    await worker_service.store_evaluation_data(task_id, request.evaluation_data)

    return {
        "success": True,
        "message": f"Evaluation data stored for task {task_id}",
        "task_id": task_id,
    }


@router.get("/evaluations")
async def list_evaluations(limit: int = 50):
    """List all evaluations.

    Args:
        limit: Maximum number of evaluations to return

    Returns:
        List of evaluations
    """
    evaluations = await worker_service.list_evaluations(limit=limit)
    return {"evaluations": evaluations, "count": len(evaluations)}


@router.get("/repositories/{repo_dir}/evaluations")
async def get_repository_evaluations(repo_dir: str):
    """Get all evaluations for a specific repository.

    Args:
        repo_dir: Directory name of the repository

    Returns:
        List of evaluations for the repository
    """
    evaluations = await worker_service.get_evaluations_by_repo(repo_dir)
    return {
        "repo_dir": repo_dir,
        "evaluations": evaluations,
        "count": len(evaluations),
    }
