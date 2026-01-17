"""Optimization workflow API endpoints."""

from fastapi import APIRouter, HTTPException

from optifiner_api.models import OptimizationWorkflowRequest
from optifiner_api.services.optimization_service import OptimizationService

router = APIRouter()

# Initialize service
optimization_service = OptimizationService()


@router.post("/optimization/start")
async def start_optimization_workflow(
    request: OptimizationWorkflowRequest,
):
    """Start an optimization workflow.

    This endpoint receives:
    - Git repository URL
    - User prompt
    - Total cost limit
    - Models with API keys and number of instances per model

    The workflow:
    1. Clones the git repository
    2. Runs baseline evaluation to get initial score
    3. Spins up worker instances per model
    4. Monitors and evaluates worker instances
    5. Selects best result and commits/pushes
    6. Iteratively improves until no improvement or cost limit reached

    Args:
        request: Optimization workflow request containing:
            - repo_url: GitHub repository URL
            - user_prompt: User prompt describing optimization goal
            - total_cost_limit: Total cost limit
            - models: List of models with provider, name, API keys, and instances
            - branch: Optional branch to clone
            - evaluator_path: Optional path to evaluator script
            - max_iterations_per_agent: Max iterations per agent
            - time_limit_seconds: Time limit per generation

    Returns:
        Workflow initialization result with workflow_id and baseline score
    """
    # Convert models to dict format
    models = [
        {
            "provider": model.provider,
            "model_name": model.model_name,
            "api_key": model.api_key,
            "instances": model.instances,
        }
        for model in request.models
    ]

    result = await optimization_service.start_optimization_workflow(
        repo_url=request.repo_url,
        branch=request.branch,
        total_cost_limit=request.total_cost_limit,
        models=models,
        user_prompt=request.user_prompt,
        evaluator_path=request.evaluator_path,
        max_iterations_per_agent=request.max_iterations_per_agent,
        time_limit_seconds=request.time_limit_seconds,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to start workflow")
        )

    return result
