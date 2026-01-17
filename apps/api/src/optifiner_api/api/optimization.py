"""Optimization workflow API endpoints.

This module provides the REST API for starting and managing optimization workflows.
It mirrors all CLI options from worker/src/worker/cli.py for feature completeness.

CLI to API Option Mapping:
    --agents (-n)         -> agents_per_generation
    --parallel (-p)       -> parallel
    --generations (-g)    -> generations
    --max-iterations (-i) -> max_iterations_per_agent
    --task (-t)          -> user_prompt
    --model-provider     -> models[].provider
    --model-name         -> models[].model_name
    --verbose (-v)       -> verbosity (0-3)
    --quiet (-q)         -> verbosity = 0
    --log-dir (-l)       -> log_dir
    --early-stop         -> early_stop
    --build-benchmark    -> build_benchmark
    --min-improvement    -> min_improvement_pct

Git operations happen on the user's repository:
    1. Clones the specified repo
    2. Creates optimization branch (optifiner-{workflow_id[:8]})
    3. Commits improvements via GitHub API
    4. Pushes to the user's repository

Example CLI command:
    python3 cli.py -p 5 -g 5 -m 10 \\
        ../../examples/volumetric_particle_sim \\
        --agents 5 \\
        --max-iterations 25 \\
        --task "Optimize this particle simulation for maximum FPS." \\
        -vvv

Equivalent API request:
    POST /api/v1/optimization/start
    {
        "repo_url": "https://github.com/user/volumetric_particle_sim",
        "parallel": 5,
        "generations": 5,
        "min_improvement_pct": 10.0,
        "agents_per_generation": 5,
        "max_iterations_per_agent": 25,
        "user_prompt": "Optimize this particle simulation for maximum FPS.",
        "verbosity": 3,
        "total_cost_limit": 10.0,
        "models": [{
            "provider": "google",
            "model_name": "gemini-2.0-flash-exp",
            "api_key": "YOUR_API_KEY"
        }]
    }
"""

import logging

from fastapi import APIRouter, HTTPException

from optifiner_api.models import OptimizationWorkflowRequest, OptimizationWorkflowStatus
from optifiner_api.services.optimization_service import OptimizationService

logger = logging.getLogger(__name__)

router = APIRouter()
optimization_service = OptimizationService()


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
    
    ## Logging Configuration (CLI options):
    - `verbosity`: Log level 0-3 (CLI: -q/-v/-vv/-vvv)
    - `log_dir`: Agent log directory (CLI: --log-dir, -l)
    
    ## Benchmark/Evaluator:
    - `evaluator_path`: Path to evaluator script
    - `build_benchmark`: Auto-create benchmark (CLI: --build-benchmark, -b)
    
    ## Git Operations:
    All commits are made to the user's repository on a new branch:
    1. Clones repository
    2. Creates branch: `optifiner-{workflow_id[:8]}`
    3. Commits improvements
    4. Pushes to remote

    Returns:
        - workflow_id: Unique workflow identifier
        - baseline_score: Initial benchmark score
        - repo_dir: Local repository directory
        - branch: Optimization branch name
        - status: "running"
    """
    try:
        logger.info(f"[API] Starting optimization: repo={request.repo_url}, agents={request.agents_per_generation}, parallel={request.parallel}, generations={request.generations}")
        
        result = await optimization_service.start_optimization_workflow(
            # Repository
            repo_url=request.repo_url,
            branch=request.branch,
            # Cost
            total_cost_limit=request.total_cost_limit,
            # Models
            models=[m.model_dump() for m in request.models],
            # Task
            user_prompt=request.user_prompt,
            # Agent config (CLI options)
            agents_per_generation=request.agents_per_generation,
            parallel=request.parallel,
            generations=request.generations,
            max_iterations_per_agent=request.max_iterations_per_agent,
            agent_types=request.agent_types,
            # Optimization settings (CLI options)
            min_improvement_pct=request.min_improvement_pct,
            early_stop=request.early_stop,
            # Benchmark (CLI options)
            evaluator_path=request.evaluator_path,
            build_benchmark=request.build_benchmark,
            # Logging (CLI options)
            verbosity=request.verbosity,
            log_dir=request.log_dir,
            # Time limit
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


@router.get("/optimization/{workflow_id}/status", response_model=OptimizationWorkflowStatus)
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
