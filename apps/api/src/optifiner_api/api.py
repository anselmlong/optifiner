"""API routes."""

from fastapi import APIRouter, HTTPException, Depends
from optifiner_api.models import (
    EvaluationDataStoreRequest,
    RepositoryCloneRequest,
    TaskSubmitRequest,
    TaskStatusResponse,
)
from optifiner_api.services.github_service import GitHubService
from optifiner_api.services.worker_service import WorkerService

router = APIRouter()

# Initialize services
github_service = GitHubService()
worker_service = WorkerService()


@router.post("/repositories/clone")
async def clone_repository(request: RepositoryCloneRequest):
    """Clone a GitHub repository.

    Args:
        request: Repository clone request

    Returns:
        Clone result
    """
    result = github_service.clone_repository(
        repo_url=request.repo_url,
        branch=request.branch,
        target_dir=request.target_dir,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Clone failed"))

    return result


@router.get("/repositories/info/{owner}/{repo_name}")
async def get_repository_info(owner: str, repo_name: str):
    """Get repository information from GitHub API.

    Args:
        owner: Repository owner
        repo_name: Repository name

    Returns:
        Repository information
    """
    result = github_service.get_repository_info(owner, repo_name)

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to get repository info")
        )

    return result


@router.post("/repositories/{repo_dir}/update")
async def update_repository(repo_dir: str):
    """Update (pull) an existing repository.

    Args:
        repo_dir: Directory name of the repository

    Returns:
        Update result
    """
    result = github_service.update_repository(repo_dir)

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Update failed")
        )

    return result


@router.get("/repositories")
async def list_repositories():
    """List all cloned repositories.

    Returns:
        List of repositories
    """
    repos = github_service.list_repositories()
    return {"repositories": repos}


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
