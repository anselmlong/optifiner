"""Optimization workflow service for orchestrating multi-model code optimization.

This service mirrors the functionality of worker/src/worker/cli.py, providing:
- Baseline evaluation
- Multi-agent optimization with configurable models
- Minimum improvement threshold to filter noise
- Step snapshots for tracking evolution history
- Early stopping when improvement found
- Git commits and pushes to user's repository

All CLI options are supported for feature completeness.
PostgreSQL is used for persistence, WebSockets for real-time updates.
"""

import asyncio
import logging
import os
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from optifiner_api.config import settings
from optifiner_api.database import get_db_context
from optifiner_api.db_models import WorkflowStatus, AgentStatus
from optifiner_api import crud
from optifiner_api.websocket import get_connection_manager
from optifiner_api.services.github_service import GitHubService

logger = logging.getLogger(__name__)

# Import worker functions from services/worker
_worker_available = False
try:
    from worker.cli import (
        run_evaluator,
        copy_workspace,
        run_single_agent_isolated,
        is_significant_improvement,
        git_commit,
        git_reset,
    )
    from worker.workspace import WorkspaceManager, set_workspace, BENCHMARK_SCRIPT_NAME
    from worker.observability import AgentObserver, set_observer
    from worker.tools.evaluate import set_benchmark_dev_mode
    from worker.benchmark_builder import run_benchmark_builder
    from worker.config import ModelConfig, ModelProvider
    _worker_available = True
except ImportError:
    # Fallback: add worker source to path for development
    _worker_src_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "worker" / "src"
    if _worker_src_path.exists() and str(_worker_src_path) not in sys.path:
        sys.path.insert(0, str(_worker_src_path))
    
    try:
        from worker.cli import (
            run_evaluator,
            copy_workspace,
            run_single_agent_isolated,
            is_significant_improvement,
            git_commit,
            git_reset,
        )
        from worker.workspace import WorkspaceManager, set_workspace, BENCHMARK_SCRIPT_NAME
        from worker.observability import AgentObserver, set_observer
        from worker.tools.evaluate import set_benchmark_dev_mode
        from worker.benchmark_builder import run_benchmark_builder
        from worker.config import ModelConfig, ModelProvider
        _worker_available = True
    except ImportError as e:
        import warnings
        warnings.warn(
            f"Failed to import worker functions: {e}. "
            f"Worker functionality will be limited. "
            f"To fix: run 'pip install -e ../../services/worker' from apps/api/"
        )
        run_evaluator = None
        copy_workspace = None
        run_single_agent_isolated = None
        is_significant_improvement = None
        git_commit = None
        git_reset = None
        BENCHMARK_SCRIPT_NAME = "optifiner_benchmark.py"

# Thread pool for running worker instances (blocking operations)
# Use a larger pool to allow more parallel agents
_executor = ThreadPoolExecutor(max_workers=20)

# Global stop event for early stopping across threads
_stop_generation = threading.Event()


class OptimizationService:
    """Service for orchestrating optimization workflows.
    
    This service provides an API that mirrors all CLI options from
    worker/src/worker/cli.py for feature completeness.
    Uses PostgreSQL for persistence and WebSockets for real-time updates.
    
    CLI Option Mapping:
        --agents (-n)         -> agents_per_generation
        --parallel (-p)       -> parallel
        --generations (-g)    -> generations
        --max-iterations (-i) -> max_iterations_per_agent
        --task (-t)          -> user_prompt
        --model-provider     -> models[].provider
        --model-name         -> models[].model_name
        --verbose (-v)       -> verbosity (0=quiet, 1=normal, 2=verbose, 3=debug)
        --quiet (-q)         -> verbosity = 0
        --log-dir (-l)       -> log_dir
        --early-stop         -> early_stop
        --build-benchmark    -> build_benchmark
        --min-improvement    -> min_improvement_pct
    """

    def __init__(self):
        """Initialize optimization service."""
        self.github_service = GitHubService()
        self.ws_manager = get_connection_manager()
        
        # Resolve workspace root path
        workspace_path = settings.WORKER_WORKSPACE_PATH
        if not Path(workspace_path).is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            self.workspace_root = project_root / workspace_path
        else:
            self.workspace_root = Path(workspace_path)
        
        # Ensure workspace directory exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        logger.debug(f"[OptimizationService] Workspace root: {self.workspace_root}")

    def _run_evaluator(
        self, evaluator_path: str | None, workspace: str, timeout: int = 120
    ) -> tuple[float | None, str | None, dict | None]:
        """Run the evaluator script and return score, error, and full data."""
        if not _worker_available or run_evaluator is None:
            return None, "Worker functions not available", None
        
        workspace_path = Path(workspace).resolve()
        if not workspace_path.exists():
            return None, f"Workspace not found: {workspace}", None
        
        if not evaluator_path:
            benchmark_path = workspace_path / BENCHMARK_SCRIPT_NAME
            if benchmark_path.exists():
                evaluator_path = str(benchmark_path)
            else:
                return None, f"No evaluator path and {BENCHMARK_SCRIPT_NAME} not found", None
        
        eval_path = Path(evaluator_path)
        if not eval_path.is_absolute():
            eval_path = workspace_path / evaluator_path
        
        if not eval_path.exists():
            return None, f"Evaluator not found: {eval_path}", None
        
        try:
            result = run_evaluator(str(eval_path), str(workspace_path), timeout, return_full_data=True)
            return result
        except Exception as e:
            return None, f"Error running evaluator: {e}", None

    def _run_benchmark_builder(
        self,
        repo_path: Path,
        model_config_dict: dict,
        verbosity: int = 1,
    ) -> tuple[bool, str, str | None]:
        """Run the benchmark builder agent to create optifiner_benchmark.py."""
        if not _worker_available:
            return False, "Worker functions not available", None
        
        provider_key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY", 
            "openai": "OPENAI_API_KEY",
        }
        api_key_env = provider_key_map.get(model_config_dict.get("provider"))
        original_key = None
        if api_key_env and model_config_dict.get("api_key"):
            original_key = os.environ.get(api_key_env)
            os.environ[api_key_env] = model_config_dict["api_key"]
        
        # Save original WORKSPACE_ROOT (if any) to restore later
        original_workspace_root = os.environ.get("WORKSPACE_ROOT")
        
        try:
            workspace_manager = WorkspaceManager(workspace_id="benchmark-builder")
            workspace_manager.setup(repo_path)
            set_workspace(workspace_manager)
            
            # Set WORKSPACE_ROOT env var as a fallback for LangGraph thread pools
            # where context vars might not propagate. This is safe because
            # benchmark builder runs sequentially (not in parallel with other agents).
            os.environ["WORKSPACE_ROOT"] = str(workspace_manager.workspace_root)
            
            observer = AgentObserver(verbosity=verbosity, console=None)
            set_observer(observer)
            
            model_name = model_config_dict.get("model_name", "gemini-2.0-flash-exp")
            model_timeout = 120.0 if "gemini" in model_name.lower() and "flash" in model_name.lower() else 60.0
            model_config = ModelConfig(
                provider=ModelProvider(model_config_dict.get("provider", "google")),
                model_name=model_name,
                temperature=0.0,
                max_tokens=8192,
                timeout=model_timeout,
                max_retries=3,
            )
            
            set_benchmark_dev_mode(True)
            success, message = run_benchmark_builder(
                workspace=workspace_manager,
                max_iterations=30,
                model_config=model_config,
                observer=observer,
            )
            
            if success:
                workspace_manager.copy_back_changes(repo_path)
                workspace_benchmark = workspace_manager.workspace_root / BENCHMARK_SCRIPT_NAME
                
                if workspace_benchmark.exists():
                    logger.info(f"[OptimizationService] Copying benchmark from workspace to repo: {workspace_benchmark} -> {repo_path / BENCHMARK_SCRIPT_NAME}")
                    shutil.copy2(workspace_benchmark, repo_path / BENCHMARK_SCRIPT_NAME)
                else:
                    # Benchmark not found in workspace - check common alternative locations
                    logger.error(
                        f"[OptimizationService] Benchmark not found at expected location: {workspace_benchmark}. "
                        f"Checking workspace contents..."
                    )
                    # List all .py files in workspace root to help diagnose
                    py_files = list(workspace_manager.workspace_root.glob("*.py"))
                    logger.error(f"[OptimizationService] Python files in workspace root: {[f.name for f in py_files]}")
                    
                    # Also check if it was written to cwd accidentally
                    cwd_benchmark = Path.cwd() / BENCHMARK_SCRIPT_NAME
                    if cwd_benchmark.exists():
                        logger.warning(
                            f"[OptimizationService] Found benchmark at cwd instead of workspace! "
                            f"Copying from {cwd_benchmark} to {repo_path / BENCHMARK_SCRIPT_NAME}"
                        )
                        shutil.copy2(cwd_benchmark, repo_path / BENCHMARK_SCRIPT_NAME)
                        # Clean up misplaced file
                        cwd_benchmark.unlink()
            
            workspace_manager.cleanup()
            set_workspace(None)
            observer.close()
            
            benchmark_path = repo_path / BENCHMARK_SCRIPT_NAME
            if success and benchmark_path.exists():
                logger.info(f"[OptimizationService] Benchmark successfully created at: {benchmark_path}")
                return True, message, str(benchmark_path)
            elif success:
                logger.error(
                    f"[OptimizationService] Benchmark builder reported success but file not found at {benchmark_path}. "
                    f"This indicates the benchmark was written to the wrong location."
                )
                return False, f"Benchmark builder succeeded but {BENCHMARK_SCRIPT_NAME} not found at {benchmark_path}", None
            else:
                return False, message, None
                
        finally:
            # Restore original WORKSPACE_ROOT
            if original_workspace_root is not None:
                os.environ["WORKSPACE_ROOT"] = original_workspace_root
            elif "WORKSPACE_ROOT" in os.environ:
                del os.environ["WORKSPACE_ROOT"]
            
            if api_key_env:
                if original_key is not None:
                    os.environ[api_key_env] = original_key
                elif api_key_env in os.environ:
                    del os.environ[api_key_env]

    async def start_optimization_workflow(
        self,
        repo_url: str,
        branch: str | None,
        total_cost_limit: float,
        models: list[dict[str, Any]],
        user_prompt: str,
        agents_per_generation: int = 10,
        parallel: int = 1,
        generations: int = 1,
        max_iterations_per_agent: int = 15,
        agent_types: list[str] | None = None,
        min_improvement_pct: float = 6.0,
        early_stop: bool = True,
        evaluator_path: str | None = None,
        build_benchmark: bool = False,
        verbosity: int = 1,
        log_dir: str | None = None,
        time_limit_seconds: int = 300,
        project_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Start an optimization workflow with full CLI feature parity.

        All git operations happen on the user's repository:
        1. Clones the specified repository
        2. Creates optimization branch (optifiner-{workflow_id[:8]})
        3. Commits improvements via GitHub API
        4. Pushes to the user's repository
        """
        if not _worker_available:
            return {"success": False, "error": "Worker functions not available"}
        
        workflow_id = uuid.uuid4()
        
        if verbosity >= 1:
            logger.info(f"[OptimizationService] Starting workflow {workflow_id}")
            logger.info(f"[OptimizationService] Repository: {repo_url}, Branch: {branch}")
            logger.info(f"[OptimizationService] Agents: {agents_per_generation}, Parallel: {parallel}, Generations: {generations}")

        # Clone repository to workspace
        clone_result = self.github_service.clone_repository(
            repo_url=repo_url,
            branch=branch,
            target_dir=None,
        )

        if not clone_result.get("success"):
            return {"success": False, "error": f"Failed to clone: {clone_result.get('error')}"}

        repo_dir = clone_result.get("repo_name")
        repo_path = self.workspace_root / repo_dir
        cloned_branch = clone_result.get("branch")

        # Create optimization branch for all commits
        optimization_branch = f"optifiner-{str(workflow_id)[:8]}"
        branch_result = self.github_service.create_branch(
            repo_dir=repo_dir,
            branch_name=optimization_branch,
            from_branch=cloned_branch,
        )

        if not branch_result.get("success"):
            return {"success": False, "error": f"Failed to create branch: {branch_result.get('error')}"}

        if verbosity >= 1:
            logger.info(f"[OptimizationService] Created optimization branch: {optimization_branch}")

        # Find or create evaluator/benchmark
        baseline_score = None
        baseline_error = None
        baseline_data = None
        resolved_evaluator_path = evaluator_path

        if evaluator_path:
            eval_path = Path(evaluator_path)
            if not eval_path.is_absolute():
                eval_path = repo_path / evaluator_path
            
            if eval_path.exists():
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    str(eval_path), str(repo_path)
                )
                resolved_evaluator_path = str(eval_path)
            else:
                baseline_error = f"Evaluator not found: {eval_path}"
        else:
            benchmark_path = repo_path / BENCHMARK_SCRIPT_NAME
            legacy_path = repo_path / "run_validator.py"
            
            if benchmark_path.exists():
                resolved_evaluator_path = str(benchmark_path)
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    resolved_evaluator_path, str(repo_path)
                )
            elif legacy_path.exists():
                resolved_evaluator_path = str(legacy_path)
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    resolved_evaluator_path, str(repo_path)
                )
            elif build_benchmark or len(models) > 0:
                if verbosity >= 1:
                    logger.info(f"[OptimizationService] No benchmark found, running benchmark builder...")
                
                builder_model = models[0] if models else {
                    "provider": "google",
                    "model_name": "gemini-2.0-flash-exp",
                    "api_key": None,
                }
                
                success, message, created_path = self._run_benchmark_builder(
                    repo_path, builder_model, verbosity
                )
                
                if success and created_path:
                    resolved_evaluator_path = created_path
                    baseline_score, baseline_error, baseline_data = self._run_evaluator(
                        resolved_evaluator_path, str(repo_path)
                    )
                else:
                    baseline_error = f"Benchmark builder failed: {message}"
            else:
                baseline_error = "No evaluator found and no models provided for benchmark builder"

        if baseline_error:
            return {"success": False, "error": f"Baseline evaluation failed: {baseline_error}"}

        if baseline_score is None:
            return {"success": False, "error": "Baseline evaluation returned no score"}

        # Log baseline (CLI style)
        if verbosity >= 1:
            logger.info(f"[OptimizationService] BASELINE EVALUATION COMPLETE")
            logger.info(f"[OptimizationService] Baseline Score: {baseline_score}")
            logger.info(f"[OptimizationService] Min Improvement Threshold: {min_improvement_pct}%")

        # Create initial git commit
        commit_hash = git_commit(str(repo_path), f"Initial state - Score: {baseline_score}")

        # Set default agent types
        if agent_types is None:
            agent_types = ["optimizer", "refactoring", "feature", "analyzer", "general"]

        # Resolve log directory
        resolved_log_dir = None
        if log_dir:
            log_path = Path(log_dir)
            if not log_path.is_absolute():
                log_path = repo_path / log_dir
            log_path.mkdir(parents=True, exist_ok=True)
            resolved_log_dir = str(log_path)

        # Create workflow in database
        async with get_db_context() as db:
            workflow = await crud.create_workflow(
                db,
                repo_url=repo_url,
                project_id=project_id,
                status=WorkflowStatus.RUNNING,
                repo_dir=repo_dir,
                branch=optimization_branch,
                original_branch=branch or cloned_branch,
                baseline_score=baseline_score,
                current_best_score=baseline_score,
                baseline_data=baseline_data,
                user_prompt=user_prompt,
                models_config=models,
                agents_per_generation=agents_per_generation,
                parallel=parallel,
                max_generations=generations,
                max_iterations_per_agent=max_iterations_per_agent,
                agent_types=agent_types,
                min_improvement_pct=min_improvement_pct,
                early_stop=early_stop,
                evaluator_path=resolved_evaluator_path,
                build_benchmark=build_benchmark,
                verbosity=verbosity,
                log_dir=resolved_log_dir,
                total_cost_limit=total_cost_limit,
                time_limit_seconds=time_limit_seconds,
                started_at=datetime.utcnow(),
                graph_data={
                    "nodes": [{
                        "id": "baseline",
                        "type": "baseline",
                        "generation": 0,
                        "score": baseline_score,
                    }],
                    "edges": [],
                },
            )
            workflow_id = workflow.id
            
            # Create initial step
            await crud.create_workflow_step(
                db,
                workflow_id=workflow_id,
                step_number=0,
                generation=0,
                agent_id="initial",
                baseline_score=baseline_score,
                final_score=baseline_score,
                improvement=0.0,
                improvement_percent=0.0,
                is_initial=True,
                commit_hash=commit_hash,
            )

        # Start workflow execution in background
        asyncio.create_task(self._execute_workflow(workflow_id))

        # Initial graph data with baseline node
        initial_graph_data = {
            "nodes": [{
                "id": "baseline",
                "type": "baseline",
                "generation": 0,
                "score": baseline_score,
                "status": "accepted",
                "label": "Baseline",
                "description": f"Initial score: {baseline_score:.2f}",
            }],
            "edges": [],
        }

        # Send initial WebSocket updates
        await self.ws_manager.send_status_update(
            str(workflow_id),
            "running",
            {
                "baseline_score": baseline_score,
                "branch": optimization_branch,
            },
        )
        
        # Send initial graph for visualization
        await self.ws_manager.send_graph_update(
            str(workflow_id),
            initial_graph_data,
        )

        return {
            "success": True,
            "workflow_id": str(workflow_id),
            "baseline_score": baseline_score,
            "repo_dir": repo_dir,
            "branch": optimization_branch,
            "status": "running",
        }

    async def _execute_workflow(self, workflow_id: UUID) -> None:
        """Execute the optimization workflow (main evolution loop)."""
        global _stop_generation
        
        try:
            # Load workflow from database
            async with get_db_context() as db:
                workflow = await crud.get_workflow(db, workflow_id)
                if not workflow:
                    logger.error(f"[OptimizationService] Workflow not found: {workflow_id}")
                    return
                
                # Extract configuration
                generation = workflow.generation
                current_best_score = workflow.baseline_score
                max_generations = workflow.max_generations
                agents_per_generation = workflow.agents_per_generation
                parallel = workflow.parallel
                min_improvement_pct = workflow.min_improvement_pct
                early_stop = workflow.early_stop
                verbosity = workflow.verbosity
                step_count = workflow.step_count
                total_improvements = workflow.total_improvements
                total_attempts = workflow.total_attempts
                repo_path = self.workspace_root / workflow.repo_dir
                models = workflow.models_config or []
                agent_types = workflow.agent_types or ["optimizer", "refactoring", "feature", "analyzer", "general"]
                
                workflow_data = workflow.to_dict()

            while generation < max_generations:
                # Check if workflow was paused/stopped
                async with get_db_context() as db:
                    current_workflow = await crud.get_workflow(db, workflow_id)
                    if current_workflow and current_workflow.status in (WorkflowStatus.PAUSED, WorkflowStatus.STOPPED):
                        return

                generation += 1
                _stop_generation.clear()

                if verbosity >= 1:
                    logger.info(f"[OptimizationService] === Generation {generation}/{max_generations} ===")
                    logger.info(f"[OptimizationService] Agents: {agents_per_generation}, Parallel: {parallel}")
                    logger.info(f"[OptimizationService] Current best score: {current_best_score}")

                # Send generation start update
                await self.ws_manager.send_workflow_update(
                    str(workflow_id),
                    "generation_start",
                    {"generation": generation, "best_score": current_best_score},
                )

                # Spawn worker instances
                instances = await self._spawn_worker_instances(
                    workflow_id, generation, workflow_data, current_best_score, models, agent_types
                )

                total_attempts += len(instances)
                
                # Update workflow in database
                async with get_db_context() as db:
                    await crud.update_workflow(
                        db, workflow_id,
                        generation=generation,
                        total_attempts=total_attempts,
                    )

                # Wait for workers to complete
                completed = await self._wait_for_workers(
                    workflow_id, instances, workflow_data.get("time_limit_seconds", 300),
                    early_stop, min_improvement_pct, current_best_score, verbosity
                )

                # Select best instance
                best = self._select_best_instance(completed, current_best_score, min_improvement_pct)

                # Copy best instance's changes back to source workspace
                if best:
                    best_result = best.get("worker_result", {})
                    workspace_manager = best_result.get("_workspace_manager")
                    if workspace_manager:
                        try:
                            for item in workspace_manager.actual_root.iterdir():
                                if item.name != ".git":
                                    dest = repo_path / item.name
                                    if item.is_dir():
                                        if dest.exists():
                                            shutil.rmtree(dest)
                                        shutil.copytree(item, dest)
                                    else:
                                        shutil.copy2(item, dest)
                            if verbosity >= 2:
                                logger.debug(f"[OptimizationService] Copied best agent's changes to {repo_path}")
                        except Exception as e:
                            logger.error(f"[OptimizationService] Failed to copy best agent's changes: {e}")

                # Clean up ALL agent workspaces (including non-completed ones)
                for inst in instances:
                    result = inst.get("worker_result", {})
                    wm = result.get("_workspace_manager")
                    if wm:
                        try:
                            wm.cleanup()
                        except Exception:
                            pass  # Ignore cleanup errors

                # Add rejected nodes for all completed instances that weren't selected
                # Determine parent node ID for rejected nodes
                parent_for_rejected = "baseline" if step_count == 0 else f"gen{generation - 1}-step{step_count}"
                rejected_nodes = []
                rejected_edges = []
                
                for idx, inst in enumerate(completed):
                    # Skip the best instance - it will be added as accepted
                    if best and inst.get("instance_id") == best.get("instance_id"):
                        continue
                    
                    result = inst.get("worker_result", {})
                    agent_score = result.get("score", 0)
                    agent_id = inst.get("instance_id", f"agent-{idx}")
                    
                    # Calculate improvement percentage for this rejected attempt
                    if current_best_score > 0:
                        rej_pct = ((agent_score - current_best_score) / current_best_score) * 100
                    else:
                        rej_pct = 0
                    
                    rejected_node = {
                        "id": f"gen{generation}-rejected-{idx}",
                        "type": "attempt",
                        "generation": generation,
                        "score": agent_score,
                        "agent_id": agent_id,
                        "status": "rejected",
                        "label": f"Agent {idx + 1}",
                        "description": f"Score: {agent_score:.2f} ({rej_pct:+.1f}%)" if agent_score else "Failed to evaluate",
                    }
                    rejected_nodes.append(rejected_node)
                    rejected_edges.append({"source": parent_for_rejected, "target": rejected_node["id"]})
                
                # Update graph with rejected nodes
                if rejected_nodes:
                    async with get_db_context() as db:
                        workflow_record = await crud.get_workflow(db, workflow_id)
                        graph_data = workflow_record.graph_data or {"nodes": [], "edges": []}
                        graph_data["nodes"].extend(rejected_nodes)
                        graph_data["edges"].extend(rejected_edges)
                        await crud.update_workflow(db, workflow_id, graph_data=graph_data)
                    
                    # Send graph update with rejected nodes
                    await self.ws_manager.send_graph_update(str(workflow_id), graph_data)

                if not best:
                    if verbosity >= 1:
                        logger.info(f"[OptimizationService] No significant improvement in generation {generation}")
                    
                    await self.ws_manager.send_log(
                        str(workflow_id), "info",
                        f"Generation {generation}: No significant improvement found",
                    )
                    continue

                # Apply improvement
                old_score = current_best_score
                current_best_score = best["evaluation_score"]
                step_count += 1
                total_improvements += 1
                
                _, improvement_pct = is_significant_improvement(old_score, current_best_score, min_improvement_pct)

                if verbosity >= 1:
                    logger.info(f"[OptimizationService] IMPROVED! {old_score:.2f} -> {current_best_score:.2f} (+{improvement_pct:.1f}%)")

                # Commit changes to user's repository
                commit_msg = f"Gen {generation} | {best['instance_id']}: +{improvement_pct:.1f}% ({old_score:.2f} -> {current_best_score:.2f})"
                commit_result = self.github_service.commit_changes(
                    repo_dir=workflow_data["repo_dir"],
                    commit_message=commit_msg,
                    branch=workflow_data["branch"],
                )

                commit_hash = None
                if commit_result.get("success"):
                    commit_hash = commit_result.get("commit_hash")
                    if verbosity >= 1:
                        logger.info(f"[OptimizationService] Committed and pushed: {commit_hash[:8] if commit_hash else 'unknown'} to {workflow_data['branch']}")
                else:
                    # commit_changes includes push, so if it failed check the error
                    error_msg = commit_result.get('error', 'Unknown error')
                    commit_hash = commit_result.get("commit_hash")  # May have committed but failed to push
                    if commit_hash:
                        logger.warning(f"[OptimizationService] Committed {commit_hash[:8]} but push failed: {error_msg}")
                    else:
                        logger.warning(f"[OptimizationService] Commit failed: {error_msg}")

                # Create step in database and update graph
                node_id = f"gen{generation}-step{step_count}"
                parent_id = "baseline" if step_count == 1 else f"gen{generation - 1}-step{step_count - 1}"
                
                # Build new node for graph
                new_node = {
                    "id": node_id,
                    "type": "improvement",
                    "generation": generation,
                    "score": current_best_score,
                    "agent_id": best["instance_id"],
                    "status": "accepted",
                    "label": f"Gen {generation}",
                    "description": f"+{improvement_pct:.1f}% ({old_score:.2f} → {current_best_score:.2f})",
                    "commit_hash": commit_hash,
                }
                new_edge = {"source": parent_id, "target": node_id}
                
                async with get_db_context() as db:
                    await crud.create_workflow_step(
                        db,
                        workflow_id=workflow_id,
                        step_number=step_count,
                        generation=generation,
                        agent_id=best["instance_id"],
                        baseline_score=old_score,
                        final_score=current_best_score,
                        improvement=current_best_score - old_score,
                        improvement_percent=improvement_pct,
                        commit_hash=commit_hash,
                    )
                    
                    # Get current graph data and update it
                    workflow_record = await crud.get_workflow(db, workflow_id)
                    graph_data = workflow_record.graph_data or {"nodes": [], "edges": []}
                    graph_data["nodes"].append(new_node)
                    graph_data["edges"].append(new_edge)
                    
                    await crud.update_workflow(
                        db, workflow_id,
                        current_best_score=current_best_score,
                        step_count=step_count,
                        total_improvements=total_improvements,
                        generation=generation,
                        graph_data=graph_data,
                    )

                # Send WebSocket updates
                await self.ws_manager.send_step_update(
                    str(workflow_id),
                    {
                        "step": step_count,
                        "generation": generation,
                        "agent_id": best["instance_id"],
                        "baseline_score": old_score,
                        "final_score": current_best_score,
                        "improvement_percent": improvement_pct,
                    },
                )
                
                # Send graph update for real-time tree visualization
                await self.ws_manager.send_graph_update(
                    str(workflow_id),
                    graph_data,
                )

                await self.ws_manager.send_log(
                    str(workflow_id), "success",
                    f"Improved! {old_score:.2f} -> {current_best_score:.2f} (+{improvement_pct:.1f}%)",
                    agent_name=best["instance_id"],
                )

            # Complete
            final_improvement = current_best_score - workflow_data["baseline_score"]
            final_pct = (final_improvement / workflow_data["baseline_score"] * 100) if workflow_data["baseline_score"] > 0 else 0

            async with get_db_context() as db:
                await crud.update_workflow_status(
                    db, workflow_id,
                    WorkflowStatus.COMPLETED,
                    improvement=final_improvement,
                    improvement_percent=final_pct,
                    current_best_score=current_best_score,
                )

            if verbosity >= 1:
                logger.info(f"[OptimizationService] OPTIMIZATION COMPLETE!")
                logger.info(f"[OptimizationService] Initial: {workflow_data['baseline_score']:.2f} -> Final: {current_best_score:.2f}")
                logger.info(f"[OptimizationService] Improvement: +{final_improvement:.2f} (+{final_pct:.1f}%)")

            # Create PR if there were improvements
            pr_url = None
            if total_improvements > 0:
                pr_title = f"[Optifiner] +{final_pct:.1f}% improvement ({workflow_data['baseline_score']:.2f} → {current_best_score:.2f})"
                pr_body = f"""## Optifiner Optimization Results

**Score Improvement:** {workflow_data['baseline_score']:.2f} → {current_best_score:.2f} (+{final_pct:.1f}%)

### Summary
- **Generations:** {generation}
- **Total Attempts:** {total_attempts}
- **Successful Improvements:** {total_improvements}

### Changes
This PR contains optimizations automatically generated by Optifiner.
Please review the changes and run your tests before merging.

---
*Generated by [Optifiner](https://github.com/optifiner)*
"""
                pr_result = self.github_service.create_pull_request(
                    repo_dir=workflow_data["repo_dir"],
                    branch=workflow_data["branch"],
                    title=pr_title,
                    body=pr_body,
                    base_branch=workflow_data.get("original_branch", "main"),
                )
                
                if pr_result.get("success"):
                    pr_url = pr_result["pull_request"]["url"]
                    logger.info(f"[OptimizationService] PR created: {pr_url}")
                    
                    # Update workflow with PR URL
                    async with get_db_context() as db:
                        await crud.update_workflow(db, workflow_id, pr_url=pr_url)
                else:
                    logger.warning(f"[OptimizationService] Failed to create PR: {pr_result.get('error')}")

            await self.ws_manager.send_status_update(
                str(workflow_id), "completed",
                {
                    "baseline_score": workflow_data["baseline_score"],
                    "final_score": current_best_score,
                    "improvement": final_improvement,
                    "improvement_percent": final_pct,
                    "pr_url": pr_url,
                },
            )

        except Exception as e:
            logger.error(f"[OptimizationService] Workflow failed: {e}", exc_info=True)
            async with get_db_context() as db:
                await crud.update_workflow_status(
                    db, workflow_id,
                    WorkflowStatus.FAILED,
                    error=str(e),
                )
            
            await self.ws_manager.send_status_update(
                str(workflow_id), "failed",
                {"error": str(e)},
            )

    async def _spawn_worker_instances(
        self,
        workflow_id: UUID,
        generation: int,
        workflow_data: dict[str, Any],
        baseline_score: float,
        models: list[dict],
        agent_types: list[str],
    ) -> list[dict[str, Any]]:
        """Spawn worker instances for the generation and run them in parallel."""
        instances = []
        total_agents = workflow_data.get("agents_per_generation", 10)
        parallel = workflow_data.get("parallel", 1)

        # Distribute agents across models
        # Priority: use explicit model instances if they sum to agents_per_generation,
        # otherwise distribute agents_per_generation evenly across models
        model_instances = []
        total_from_models = sum(m.get("instances", 0) for m in models)
        
        if total_from_models >= total_agents:
            # Model configs fully specify agent distribution
            for model in models:
                for _ in range(model.get("instances", 0)):
                    model_instances.append(model)
        else:
            # Distribute total_agents evenly across models (ignoring model.instances)
            per_model = max(1, total_agents // len(models)) if models else 0
            for idx, model in enumerate(models):
                count = per_model + (1 if idx < (total_agents - per_model * len(models)) else 0)
                for _ in range(count):
                    model_instances.append(model)

        # Create all agent instances in database first
        async with get_db_context() as db:
            for i, model in enumerate(model_instances):
                agent_type = agent_types[i % len(agent_types)]
                instance_id = f"{str(workflow_id)[:8]}-gen{generation}-{agent_type}-{i+1}"
                
                agent = await crud.create_agent_instance(
                    db,
                    workflow_id=workflow_id,
                    instance_id=instance_id,
                    generation=generation,
                    agent_type=agent_type,
                    model_provider=model["provider"],
                    model_name=model["model_name"],
                    baseline_score=baseline_score,
                )
                
                instance = {
                    "db_id": str(agent.id),
                    "instance_id": instance_id,
                    "generation": generation,
                    "model_provider": model["provider"],
                    "model_name": model["model_name"],
                    "api_key": model.get("api_key"),
                    "agent_type": agent_type,
                    "status": "pending",
                    "started_at": datetime.now().isoformat(),
                }
                instances.append(instance)
                
                await self.ws_manager.send_agent_update(
                    str(workflow_id),
                    {"instance_id": instance_id, "status": "pending", "agent_type": agent_type},
                )

        # Run workers in parallel with concurrency limit
        repo_path = self.workspace_root / workflow_data["repo_dir"]
        semaphore = asyncio.Semaphore(parallel)
        
        logger.info(f"[OptimizationService] Running {len(instances)} agents with parallelism={parallel}")
        
        async def run_with_semaphore(instance: dict) -> None:
            """Run worker with semaphore to limit concurrency."""
            async with semaphore:
                await self._run_worker_instance(
                    workflow_id, instance, str(repo_path), workflow_data, baseline_score
                )
        
        # Create all tasks and run them in parallel (limited by semaphore)
        tasks = [asyncio.create_task(run_with_semaphore(inst)) for inst in instances]
        
        # Don't await here - let _wait_for_workers handle waiting with early stop logic
        # Store tasks in instances for tracking
        for inst, task in zip(instances, tasks):
            inst["_task"] = task

        return instances

    async def _run_worker_instance(
        self,
        workflow_id: UUID,
        instance: dict[str, Any],
        source_workspace: str,
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> None:
        """Run a single worker instance."""
        global _stop_generation
        
        db_id = UUID(instance["db_id"])
        
        try:
            # Update status to running
            async with get_db_context() as db:
                await crud.update_agent_status(db, db_id, AgentStatus.RUNNING)
            
            await self.ws_manager.send_agent_update(
                str(workflow_id),
                {"instance_id": instance["instance_id"], "status": "running"},
            )
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._run_worker_instance_sync,
                instance,
                source_workspace,
                workflow_data,
                baseline_score,
            )
            instance["worker_result"] = result
            instance["completed_at"] = datetime.now().isoformat()
            
            # Update database
            async with get_db_context() as db:
                await crud.update_agent_status(
                    db, db_id,
                    AgentStatus.COMPLETED if result.get("success") else AgentStatus.FAILED,
                    final_score=result.get("score"),
                    improvement=result.get("improvement", 0),
                    success=result.get("success", False),
                    error=result.get("error"),
                )
            
            await self.ws_manager.send_agent_update(
                str(workflow_id),
                {
                    "instance_id": instance["instance_id"],
                    "status": "completed" if result.get("success") else "failed",
                    "score": result.get("score"),
                    "success": result.get("success"),
                },
            )
            
        except Exception as e:
            instance["error"] = str(e)
            instance["completed_at"] = datetime.now().isoformat()
            
            async with get_db_context() as db:
                await crud.update_agent_status(
                    db, db_id, AgentStatus.FAILED,
                    error=str(e),
                )
            
            await self.ws_manager.send_agent_update(
                str(workflow_id),
                {"instance_id": instance["instance_id"], "status": "failed", "error": str(e)},
            )

    def _run_worker_instance_sync(
        self,
        instance: dict[str, Any],
        source_workspace: str,
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> dict[str, Any]:
        """Run worker instance synchronously."""
        global _stop_generation
        
        if not _worker_available or run_single_agent_isolated is None:
            return {"success": False, "error": "Worker not available", "score": baseline_score}

        # Verify benchmark exists in source workspace before running agent
        evaluator_path = workflow_data.get("evaluator_path")
        if evaluator_path:
            eval_filename = os.path.basename(evaluator_path)
            if eval_filename == BENCHMARK_SCRIPT_NAME:
                # In-workspace benchmark - verify it exists in source
                source_benchmark = Path(source_workspace) / BENCHMARK_SCRIPT_NAME
                if not source_benchmark.exists():
                    logger.error(
                        f"[OptimizationService] Benchmark not found in source workspace: {source_benchmark}. "
                        f"This indicates a problem with benchmark builder or copy-back process."
                    )
                    return {
                        "success": False,
                        "error": f"Benchmark script not found in source: {source_benchmark}",
                        "score": baseline_score,
                    }

        # Set API key
        provider_key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        api_key_env = provider_key_map.get(instance["model_provider"])
        original_key = None
        if api_key_env and instance.get("api_key"):
            original_key = os.environ.get(api_key_env)
            os.environ[api_key_env] = instance["api_key"]

        try:
            agent_result, workspace_manager = run_single_agent_isolated(
                source_workspace=source_workspace,
                evaluator_path=workflow_data.get("evaluator_path"),
                agent_type=instance.get("agent_type", "optimizer"),
                agent_id=instance["instance_id"],
                baseline_score=baseline_score,
                task=workflow_data.get("user_prompt", "Improve the code to get a higher benchmark score."),
                max_iterations=workflow_data.get("max_iterations_per_agent", 15),
                model_provider=instance["model_provider"],
                model_name=instance["model_name"],
                verbosity=workflow_data.get("verbosity", 1),
                log_dir=workflow_data.get("log_dir"),
                baseline_data=workflow_data.get("baseline_data"),
                min_improvement_pct=workflow_data.get("min_improvement_pct", 6.0),
                stop_event=_stop_generation if workflow_data.get("early_stop") else None,
                compact=workflow_data.get("parallel", 1) > 1,
            )

            result = {
                "success": agent_result.success,
                "score": agent_result.final_score if agent_result.success else baseline_score,
                "improvement": agent_result.improvement if agent_result.success else 0.0,
                "error": agent_result.error,
            }

            # Keep workspace alive for now - copy-back happens after best selection
            # to avoid race conditions where a less-improved agent overwrites a better one.
            # Store workspace_manager reference; cleanup happens in _select_best_instance.
            if workspace_manager:
                result["_workspace_manager"] = workspace_manager
                result["_workspace_path"] = str(workspace_manager.actual_root)

            return result

        finally:
            if api_key_env:
                if original_key is not None:
                    os.environ[api_key_env] = original_key
                elif api_key_env in os.environ:
                    del os.environ[api_key_env]

    async def _wait_for_workers(
        self,
        workflow_id: UUID,
        instances: list[dict[str, Any]],
        time_limit: int,
        early_stop: bool,
        min_improvement_pct: float,
        current_best_score: float,
        verbosity: int,
    ) -> list[dict[str, Any]]:
        """Wait for workers to complete or time limit."""
        global _stop_generation
        
        start_time = time.time()
        early_stop_triggered = False

        while time.time() - start_time < time_limit:
            completed = [i for i in instances if i.get("completed_at")]
            pending = len(instances) - len(completed)
            
            if verbosity >= 2:
                logger.debug(f"[OptimizationService] Waiting: {len(completed)}/{len(instances)} completed, {pending} pending")
            
            if len(completed) == len(instances):
                logger.info(f"[OptimizationService] All {len(instances)} agents completed")
                break

            # Check for early stop
            if early_stop and not early_stop_triggered:
                for inst in completed:
                    result = inst.get("worker_result", {})
                    if result.get("success") and result.get("score"):
                        is_sig, pct = is_significant_improvement(
                            current_best_score, result["score"], min_improvement_pct
                        )
                        if is_sig:
                            if verbosity >= 1:
                                logger.info(f"[OptimizationService] Early stop triggered: +{pct:.1f}% improvement found")
                            _stop_generation.set()
                            early_stop_triggered = True
                            
                            await self.ws_manager.send_log(
                                str(workflow_id), "info",
                                f"Early stop: +{pct:.1f}% improvement found, signaling other agents to stop",
                            )
                            break

            # If early stop triggered, wait a bit for running agents to notice and complete
            if early_stop_triggered:
                # Give agents up to 10 seconds to notice the stop event and complete
                await asyncio.sleep(1)
                # Check if all tasks completed
                completed = [i for i in instances if i.get("completed_at")]
                if len(completed) == len(instances):
                    break
                # After 10 seconds of early stop, just return what we have
                if time.time() - start_time > 10:
                    logger.info(f"[OptimizationService] Early stop timeout, returning {len(completed)} completed agents")
                    break

            await asyncio.sleep(0.5)

        # Return all completed instances
        completed = [i for i in instances if i.get("completed_at")]
        logger.info(f"[OptimizationService] Generation complete: {len(completed)}/{len(instances)} agents finished")
        return completed

    def _select_best_instance(
        self,
        instances: list[dict[str, Any]],
        baseline_score: float,
        min_improvement_pct: float,
    ) -> dict[str, Any] | None:
        """Select the best significantly improved instance."""
        improved = []
        for inst in instances:
            result = inst.get("worker_result", {})
            score = result.get("score")
            if score and result.get("success"):
                is_sig, pct = is_significant_improvement(baseline_score, score, min_improvement_pct)
                if is_sig:
                    inst["evaluation_score"] = score
                    inst["_improvement_pct"] = pct
                    improved.append(inst)

        if not improved:
            return None

        improved.sort(key=lambda x: x["evaluation_score"], reverse=True)
        return improved[0]

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """Get workflow status."""
        try:
            wf_uuid = UUID(workflow_id)
        except ValueError:
            return None
        
        async with get_db_context() as db:
            workflow = await crud.get_workflow(db, wf_uuid)
            if not workflow:
                return None
            return workflow.to_dict()

    async def pause_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Pause an active workflow."""
        try:
            wf_uuid = UUID(workflow_id)
        except ValueError:
            return {"success": False, "error": "Invalid workflow ID"}
        
        async with get_db_context() as db:
            workflow = await crud.get_workflow(db, wf_uuid)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            if workflow.status != WorkflowStatus.RUNNING:
                return {"success": False, "error": f"Workflow not running: {workflow.status.value}"}
            
            await crud.update_workflow_status(db, wf_uuid, WorkflowStatus.PAUSED)
        
        await self.ws_manager.send_status_update(workflow_id, "paused")
        return {"success": True, "status": "paused"}

    async def resume_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Resume a paused workflow."""
        try:
            wf_uuid = UUID(workflow_id)
        except ValueError:
            return {"success": False, "error": "Invalid workflow ID"}
        
        async with get_db_context() as db:
            workflow = await crud.get_workflow(db, wf_uuid)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            if workflow.status != WorkflowStatus.PAUSED:
                return {"success": False, "error": f"Workflow not paused: {workflow.status.value}"}
            
            await crud.update_workflow_status(db, wf_uuid, WorkflowStatus.RUNNING)
        
        # Resume execution
        asyncio.create_task(self._execute_workflow(wf_uuid))
        
        await self.ws_manager.send_status_update(workflow_id, "running")
        return {"success": True, "status": "running"}

    async def stop_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Stop a workflow completely."""
        try:
            wf_uuid = UUID(workflow_id)
        except ValueError:
            return {"success": False, "error": "Invalid workflow ID"}
        
        async with get_db_context() as db:
            workflow = await crud.get_workflow(db, wf_uuid)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            
            await crud.update_workflow_status(db, wf_uuid, WorkflowStatus.STOPPED)
            final_score = workflow.current_best_score
        
        await self.ws_manager.send_status_update(
            workflow_id, "stopped",
            {"final_score": final_score},
        )
        
        return {
            "success": True,
            "status": "stopped",
            "final_score": final_score,
        }

    async def list_workflows(
        self,
        project_id: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List workflows with optional filtering."""
        async with get_db_context() as db:
            proj_uuid = UUID(project_id) if project_id else None
            wf_status = WorkflowStatus(status) if status else None
            
            workflows = await crud.get_workflows(
                db,
                project_id=proj_uuid,
                status=wf_status,
                skip=skip,
                limit=limit,
            )
            
            return [w.to_dict() for w in workflows]

    async def get_workflow_logs(
        self,
        workflow_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get logs for a workflow."""
        try:
            wf_uuid = UUID(workflow_id)
        except ValueError:
            return []
        
        async with get_db_context() as db:
            logs = await crud.get_workflow_logs(db, wf_uuid, limit=limit)
            return [log.to_dict() for log in logs]
