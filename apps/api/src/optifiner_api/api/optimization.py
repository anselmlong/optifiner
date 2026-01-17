"""Optimization workflow API endpoints.

This module provides the REST API for starting and managing optimization workflows.
It mirrors all CLI options from worker/src/worker/cli.py for feature completeness.

Uses PostgreSQL for persistence and WebSockets for real-time updates.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from optifiner_api.models import OptimizationWorkflowRequest, OptimizationWorkflowStatus
from optifiner_api.services.optimization_service import OptimizationService
from optifiner_api.database import get_db_context
from optifiner_api import crud

logger = logging.getLogger(__name__)

router = APIRouter()
optimization_service = OptimizationService()


# =============================================================================
# Workflow Endpoints
# =============================================================================

@router.post("/optimization/start")
async def start_optimization_workflow(request: OptimizationWorkflowRequest):
    """Start an optimization workflow with full CLI feature parity.

    This endpoint mirrors all functionality from worker/src/worker/cli.py.

    ## Agent Configuration (CLI options):
    - `agents_per_generation`: Number of agents per generation (CLI: --agents, -n)
    - `parallel`: Parallel execution count (CLI: --parallel, -p)
    - `generations`: Max evolution generations (CLI: --generations, -g)
    - `max_iterations_per_agent`: Iterations per agent (CLI: --max-iterations, -i)
    - `agent_types`: Agent types to cycle through (default: optimizer, refactoring, feature, analyzer, general)
    
    ## Optimization Settings (CLI options):
    - `min_improvement_pct`: Noise filter threshold (CLI: --min-improvement, -m, default: 6.0%)
    - `early_stop`: Stop on improvement (CLI: --early-stop/--no-early-stop)
    - `user_prompt`: Task description (CLI: --task, -t)

    Returns:
        - workflow_id: Unique workflow identifier
        - baseline_score: Initial benchmark score
        - repo_dir: Local repository directory
        - branch: Optimization branch name
        - status: "running"
    
    WebSocket: Connect to /ws/workflow/{workflow_id} for real-time updates.
    """
    try:
        logger.info(f"[API] Starting optimization: repo={request.repo_url}, agents={request.agents_per_generation}, parallel={request.parallel}, generations={request.generations}")
        
        result = await optimization_service.start_optimization_workflow(
            repo_url=request.repo_url,
            branch=request.branch,
            total_cost_limit=request.total_cost_limit,
            models=[m.model_dump() for m in request.models],
            user_prompt=request.user_prompt,
            agents_per_generation=request.agents_per_generation,
            parallel=request.parallel,
            generations=request.generations,
            max_iterations_per_agent=request.max_iterations_per_agent,
            agent_types=request.agent_types,
            min_improvement_pct=request.min_improvement_pct,
            early_stop=request.early_stop,
            evaluator_path=request.evaluator_path,
            build_benchmark=request.build_benchmark,
            verbosity=request.verbosity,
            log_dir=request.log_dir,
            time_limit_seconds=request.time_limit_seconds,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        logger.info(f"[API] Workflow started: id={result.get('workflow_id')}, branch={result.get('branch')}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization/workflows")
async def list_workflows(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all workflows with optional filtering."""
    try:
        workflows = await optimization_service.list_workflows(
            project_id=project_id,
            status=status,
            skip=skip,
            limit=limit,
        )
        return {"workflows": workflows, "total": len(workflows)}
    except Exception as e:
        logger.error(f"[API] Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization/{workflow_id}/status")
async def get_optimization_status(workflow_id: str):
    """Get the current status of an optimization workflow.

    Returns complete workflow status including:
    - Current generation and progress
    - Best score achieved
    - Step snapshots with metadata
    - Cost tracking
    - Timing information
    """
    result = await optimization_service.get_workflow_status(workflow_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return result


@router.get("/optimization/{workflow_id}/logs")
async def get_workflow_logs(
    workflow_id: str,
    limit: int = Query(100, ge=1, le=1000),
):
    """Get logs for a workflow."""
    logs = await optimization_service.get_workflow_logs(workflow_id, limit=limit)
    return {"logs": logs}


@router.post("/optimization/{workflow_id}/pause")
async def pause_optimization_workflow(workflow_id: str):
    """Pause an active optimization workflow.
    
    The workflow can be resumed later with the /resume endpoint.
    Current generation will complete but no new generations start.
    """
    result = await optimization_service.pause_workflow(workflow_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/optimization/{workflow_id}/resume")
async def resume_optimization_workflow(workflow_id: str):
    """Resume a paused optimization workflow.
    
    Continues from where the workflow was paused.
    """
    result = await optimization_service.resume_workflow(workflow_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/optimization/{workflow_id}/stop")
async def stop_optimization_workflow(workflow_id: str):
    """Stop an optimization workflow completely.
    
    Returns final results including best score achieved.
    """
    result = await optimization_service.stop_workflow(workflow_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# =============================================================================
# Project Endpoints
# =============================================================================

@router.get("/projects")
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all projects."""
    try:
        async with get_db_context() as db:
            projects = await crud.get_projects(db, skip=skip, limit=limit, status=status)
            return {
                "projects": [p.to_dict() for p in projects],
                "total": len(projects),
            }
    except Exception as e:
        logger.error(f"[API] Error listing projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects")
async def create_project(
    name: str,
    description: Optional[str] = None,
    repository_url: Optional[str] = None,
    repository_branch: Optional[str] = None,
    target_fitness: float = 0.95,
    cost_limit: float = 50.0,
):
    """Create a new project."""
    try:
        async with get_db_context() as db:
            project = await crud.create_project(
                db,
                name=name,
                description=description,
                repository_url=repository_url,
                repository_branch=repository_branch,
                target_fitness=target_fitness,
                cost_limit=cost_limit,
            )
            return project.to_dict()
    except Exception as e:
        logger.error(f"[API] Error creating project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a project by ID."""
    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    async with get_db_context() as db:
        project = await crud.get_project(db, proj_uuid)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.to_dict()


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    target_fitness: Optional[float] = None,
    cost_limit: Optional[float] = None,
):
    """Update a project."""
    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if status is not None:
        update_data["status"] = status
    if target_fitness is not None:
        update_data["target_fitness"] = target_fitness
    if cost_limit is not None:
        update_data["cost_limit"] = cost_limit
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    async with get_db_context() as db:
        project = await crud.update_project(db, proj_uuid, **update_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project.to_dict()


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID")
    
    async with get_db_context() as db:
        success = await crud.delete_project(db, proj_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True}


@router.get("/projects/{project_id}/workflows")
async def get_project_workflows(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Get all workflows for a project."""
    try:
        workflows = await optimization_service.list_workflows(
            project_id=project_id,
            skip=skip,
            limit=limit,
        )
        return {"workflows": workflows, "total": len(workflows)}
    except Exception as e:
        logger.error(f"[API] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Dashboard/Stats Endpoints
# =============================================================================

@router.get("/stats/dashboard")
async def get_dashboard_stats():
    """Get dashboard statistics."""
    try:
        async with get_db_context() as db:
            all_projects = await crud.get_projects(db, limit=1000)
            active_projects = [p for p in all_projects if p.status == "active"]
            paused_projects = [p for p in all_projects if p.status == "paused"]
            completed_projects = [p for p in all_projects if p.status == "completed"]
            
            from optifiner_api.db_models import WorkflowStatus
            running_workflows = await crud.get_workflows(db, status=WorkflowStatus.RUNNING, limit=1000)
            
            total_cost = sum(p.total_cost_spent for p in all_projects)
            
            return {
                "projects": {
                    "total": len(all_projects),
                    "active": len(active_projects),
                    "paused": len(paused_projects),
                    "completed": len(completed_projects),
                },
                "workflows": {
                    "running": len(running_workflows),
                },
                "cost": {
                    "total_spent": total_cost,
                },
            }
    except Exception as e:
        logger.error(f"[API] Error getting dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
