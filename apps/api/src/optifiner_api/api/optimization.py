"""Optimization workflow API endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from optifiner_api.models import OptimizationWorkflowRequest, OptimizationWorkflowStatus
from optifiner_api.services.optimization_service import OptimizationService

logger = logging.getLogger(__name__)

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
    try:
        logger.debug(f"[API] /optimization/start called with repo_url={request.repo_url}, branch={request.branch}, models={len(request.models)}")
        
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
        
        logger.debug(f"[API] Converted {len(models)} models to dict format")

        logger.debug(f"[API] Calling optimization_service.start_optimization_workflow")
        result = await optimization_service.start_optimization_workflow(
            repo_url=request.repo_url,
            branch=request.branch,
            total_cost_limit=request.total_cost_limit,
            models=models,
            user_prompt=request.user_prompt,
            evaluator_path=request.evaluator_path,
            max_iterations_per_agent=request.max_iterations_per_agent,
            time_limit_seconds=request.time_limit_seconds,
            min_improvement_pct=request.min_improvement_pct,
            early_stop=request.early_stop,
        )
        
        logger.debug(f"[API] start_optimization_workflow returned: success={result.get('success')}, workflow_id={result.get('workflow_id')}")

        if not result.get("success"):
            error_msg = result.get("error", "Failed to start workflow")
            logger.error(f"[API] Workflow start failed: {error_msg}")
            raise HTTPException(
                status_code=400, detail=error_msg
            )

        logger.info(f"[API] Workflow started successfully: workflow_id={result.get('workflow_id')}")
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"[API] Unexpected error in start_optimization_workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


@router.post("/optimization/{workflow_id}/pause")
async def pause_optimization_workflow(workflow_id: str):
    """Pause an active optimization workflow.
    
    Args:
        workflow_id: The ID of the workflow to pause
        
    Returns:
        Status confirmation
    """
    result = await optimization_service.pause_workflow(workflow_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to pause workflow")
        )
    
    return result


@router.post("/optimization/{workflow_id}/resume")
async def resume_optimization_workflow(workflow_id: str):
    """Resume a paused optimization workflow.
    
    Args:
        workflow_id: The ID of the workflow to resume
        
    Returns:
        Status confirmation
    """
    result = await optimization_service.resume_workflow(workflow_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to resume workflow")
        )
    
    return result


@router.get("/optimization/{workflow_id}/status", response_model=OptimizationWorkflowStatus)
async def get_optimization_status(workflow_id: str):
    """Get the current status of an optimization workflow.
    
    Args:
        workflow_id: The ID of the workflow
        
    Returns:
        Current workflow status including progress, costs, and tree data
    """
    result = await optimization_service.get_workflow_status(workflow_id)
    
    if not result:
        raise HTTPException(
            status_code=404, detail="Workflow not found"
        )
    
    return result


@router.post("/optimization/{workflow_id}/stop")
async def stop_optimization_workflow(workflow_id: str):
    """Stop an optimization workflow completely.
    
    Args:
        workflow_id: The ID of the workflow to stop
        
    Returns:
        Final status and results
    """
    result = await optimization_service.stop_workflow(workflow_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to stop workflow")
        )
    
    return result
