"""Optimization workflow service for orchestrating multi-model code optimization.

This service mirrors the functionality of worker/src/worker/cli.py, providing:
- Baseline evaluation
- Multi-agent optimization with configurable models
- Minimum improvement threshold to filter noise
- Step snapshots for tracking evolution history
- Early stopping when improvement found
- Git commits and pushes to user's repository

All CLI options are supported for feature completeness.
"""

import asyncio
import json
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

import redis.asyncio as redis

from optifiner_api.config import settings
from optifiner_api.services.github_service import GitHubService

logger = logging.getLogger(__name__)

# Import worker functions from services/worker
# First try importing from installed package (if worker was installed via pip install -e)
# Then fall back to adding worker source to path for development
_worker_available = False
try:
    from worker.cli import (
        run_evaluator,
        copy_workspace,
        run_single_agent_isolated,
        is_significant_improvement,
        save_step_snapshot,
        save_initial_snapshot,
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
            save_step_snapshot,
            save_initial_snapshot,
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
        save_step_snapshot = None
        save_initial_snapshot = None
        git_commit = None
        git_reset = None
        BENCHMARK_SCRIPT_NAME = "optifiner_benchmark.py"

# Thread pool for running worker instances (blocking operations)
_executor = ThreadPoolExecutor(max_workers=10)

# Global stop event for early stopping across threads
_stop_generation = threading.Event()


class OptimizationService:
    """Service for orchestrating optimization workflows.
    
    This service provides an API that mirrors all CLI options from
    worker/src/worker/cli.py for feature completeness.
    
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
        self.redis_client: redis.Redis | None = None
        self.github_service = GitHubService()
        
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

    async def connect(self):
        """Connect to Redis."""
        if not self.redis_client:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL, decode_responses=True
            )

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

    def _run_evaluator(
        self, evaluator_path: str | None, workspace: str, timeout: int = 120
    ) -> tuple[float | None, str | None, dict | None]:
        """Run the evaluator script and return score, error, and full data.

        Args:
            evaluator_path: Path to the evaluator script
            workspace: Path to the workspace to evaluate
            timeout: Timeout in seconds

        Returns:
            Tuple of (score, error, data)
        """
        if not _worker_available or run_evaluator is None:
            return None, "Worker functions not available", None
        
        workspace_path = Path(workspace).resolve()
        if not workspace_path.exists():
            return None, f"Workspace not found: {workspace}", None
        
        # If evaluator_path is None, check for benchmark in workspace
        if not evaluator_path:
            benchmark_path = workspace_path / BENCHMARK_SCRIPT_NAME
            if benchmark_path.exists():
                evaluator_path = str(benchmark_path)
            else:
                return None, f"No evaluator path and {BENCHMARK_SCRIPT_NAME} not found", None
        
        # Resolve evaluator path
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
        """Run the benchmark builder agent to create optifiner_benchmark.py.
        
        Args:
            repo_path: Path to the repository
            model_config_dict: Model configuration dict with provider, model_name, api_key
            verbosity: Logging verbosity level
            
        Returns:
            Tuple of (success, message, evaluator_path)
        """
        if not _worker_available:
            return False, "Worker functions not available", None
        
        # Set up API key in environment
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
        
        try:
            # Create workspace manager
            workspace_manager = WorkspaceManager(workspace_id="benchmark-builder")
            workspace_manager.setup(repo_path)
            set_workspace(workspace_manager)
            
            # Set up observer
            observer = AgentObserver(verbosity=verbosity, console=None)
            set_observer(observer)
            
            # Configure model
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
            
            # Run benchmark builder
            set_benchmark_dev_mode(True)
            success, message = run_benchmark_builder(
                workspace=workspace_manager,
                max_iterations=30,
                model_config=model_config,
                observer=observer,
            )
            
            # Copy changes back to repo
            if success:
                workspace_manager.copy_back_changes(repo_path)
            
            # Cleanup
            workspace_manager.cleanup()
            set_workspace(None)
            observer.close()
            
            benchmark_path = repo_path / BENCHMARK_SCRIPT_NAME
            if success and benchmark_path.exists():
                return True, message, str(benchmark_path)
            elif success:
                return False, f"Benchmark builder succeeded but {BENCHMARK_SCRIPT_NAME} not found", None
            else:
                return False, message, None
                
        finally:
            # Restore original API key
            if api_key_env:
                if original_key is not None:
                    os.environ[api_key_env] = original_key
                elif api_key_env in os.environ:
                    del os.environ[api_key_env]

    async def start_optimization_workflow(
        self,
        # Repository configuration
        repo_url: str,
        branch: str | None,
        # Cost limit
        total_cost_limit: float,
        # Model configuration
        models: list[dict[str, Any]],
        # Task configuration (CLI: --task)
        user_prompt: str,
        # Agent configuration (CLI options)
        agents_per_generation: int = 10,  # CLI: --agents
        parallel: int = 1,  # CLI: --parallel
        generations: int = 1,  # CLI: --generations
        max_iterations_per_agent: int = 15,  # CLI: --max-iterations
        agent_types: list[str] | None = None,  # CLI cycles through these
        # Optimization settings (CLI options)
        min_improvement_pct: float = 6.0,  # CLI: --min-improvement
        early_stop: bool = True,  # CLI: --early-stop
        # Benchmark configuration (CLI options)
        evaluator_path: str | None = None,
        build_benchmark: bool = False,  # CLI: --build-benchmark
        # Logging configuration (CLI options)
        verbosity: int = 1,  # CLI: -v count or -q
        log_dir: str | None = None,  # CLI: --log-dir
        # Time limits
        time_limit_seconds: int = 300,
    ) -> dict[str, Any]:
        """Start an optimization workflow with full CLI feature parity.

        All git operations happen on the user's repository:
        1. Clones the specified repository
        2. Creates optimization branch (optifiner-{workflow_id[:8]})
        3. Commits improvements via GitHub API
        4. Pushes to the user's repository

        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone (default: repository default branch)
            total_cost_limit: Total cost limit for the optimization
            models: List of model configurations
            user_prompt: Task description (CLI: --task)
            agents_per_generation: Agents per generation (CLI: --agents, default 10)
            parallel: Parallel execution count (CLI: --parallel, default 1)
            generations: Max generations (CLI: --generations, default 1)
            max_iterations_per_agent: Iterations per agent (CLI: --max-iterations, default 15)
            agent_types: Agent types to cycle through
            min_improvement_pct: Noise threshold (CLI: --min-improvement, default 6.0%)
            early_stop: Stop on improvement (CLI: --early-stop, default True)
            evaluator_path: Path to evaluator script
            build_benchmark: Auto-create benchmark (CLI: --build-benchmark)
            verbosity: Log level 0-3 (CLI: -q/-v/-vv/-vvv, default 1)
            log_dir: Agent log directory (CLI: --log-dir)
            time_limit_seconds: Time limit per generation

        Returns:
            Dictionary with workflow_id, baseline_score, branch, status
        """
        if not _worker_available:
            return {"success": False, "error": "Worker functions not available"}
        
        await self.connect()
        workflow_id = str(uuid.uuid4())
        
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
        optimization_branch = f"optifiner-{workflow_id[:8]}"
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

        if evaluator_path:
            # Evaluator provided - verify and run baseline
            eval_path = Path(evaluator_path)
            if not eval_path.is_absolute():
                eval_path = repo_path / evaluator_path
            
            if eval_path.exists():
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    str(eval_path), str(repo_path)
                )
                evaluator_path = str(eval_path)
            else:
                baseline_error = f"Evaluator not found: {eval_path}"
        else:
            # Check for existing benchmark
            benchmark_path = repo_path / BENCHMARK_SCRIPT_NAME
            legacy_path = repo_path / "run_validator.py"
            
            if benchmark_path.exists():
                evaluator_path = str(benchmark_path)
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    evaluator_path, str(repo_path)
                )
            elif legacy_path.exists():
                evaluator_path = str(legacy_path)
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    evaluator_path, str(repo_path)
                )
            elif build_benchmark or len(models) > 0:
                # Run benchmark builder
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
                    evaluator_path = created_path
                    baseline_score, baseline_error, baseline_data = self._run_evaluator(
                        evaluator_path, str(repo_path)
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
            logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
            logger.info(f"[OptimizationService] BASELINE EVALUATION COMPLETE")
            logger.info(f"[OptimizationService] Baseline Score: {baseline_score}")
            logger.info(f"[OptimizationService] Min Improvement Threshold: {min_improvement_pct}%")
            if baseline_data:
                if "fps" in baseline_data:
                    logger.info(f"[OptimizationService]   FPS: {baseline_data['fps']:.2f}")
                if baseline_data.get("metrics"):
                    for k, v in baseline_data["metrics"].items():
                        if k != "fps":
                            logger.info(f"[OptimizationService]   {k}: {v}")
            logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")

        # Save initial snapshot (step 0)
        save_initial_snapshot(repo_path, repo_path, baseline_score, console=None)

        # Create initial git commit
        commit_hash = git_commit(str(repo_path), f"Initial state - Score: {baseline_score}")
        if commit_hash and verbosity >= 1:
            logger.info(f"[OptimizationService] Created initial commit: {commit_hash}")

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

        # Store workflow state
        workflow_key = f"optimization_workflow:{workflow_id}"
        workflow_data = {
            "workflow_id": workflow_id,
            "status": "running",
            "repo_url": repo_url,
            "repo_dir": repo_dir,
            "branch": optimization_branch,
            "original_branch": branch,
            "baseline_score": baseline_score,
            "baseline_data": baseline_data or {},
            "current_best_score": baseline_score,
            # Agent configuration
            "agents_per_generation": agents_per_generation,
            "parallel": parallel,
            "max_generations": generations,
            "agent_types": agent_types,
            "max_iterations_per_agent": max_iterations_per_agent,
            # Progress tracking
            "generation": 0,
            "total_improvements": 0,
            "total_attempts": 0,
            "step_count": 0,
            "steps": [{
                "step": 0,
                "generation": 0,
                "agent_id": "initial",
                "baseline_score": baseline_score,
                "final_score": baseline_score,
                "improvement": 0.0,
                "improvement_percent": 0.0,
                "timestamp": datetime.now().isoformat(),
                "is_initial": True,
            }],
            # Configuration
            "models": models,
            "user_prompt": user_prompt,
            "evaluator_path": evaluator_path,
            "min_improvement_pct": min_improvement_pct,
            "early_stop": early_stop,
            "verbosity": verbosity,
            "log_dir": resolved_log_dir,
            "total_cost_limit": total_cost_limit,
            "total_cost": 0.0,
            "time_limit_seconds": time_limit_seconds,
            # Worker instances
            "worker_instances": [],
            # Timing
            "started_at": datetime.now().isoformat(),
            # Graph structure
            "graph_data": {
                "nodes": [{
                    "id": "baseline",
                    "type": "baseline",
                    "generation": 0,
                    "score": baseline_score,
                }],
                "edges": [],
            },
        }

        await self.redis_client.setex(workflow_key, 7200, json.dumps(workflow_data))

        # Start workflow execution in background
        asyncio.create_task(self._execute_workflow(workflow_id, workflow_data))

        return {
            "success": True,
            "workflow_id": workflow_id,
            "baseline_score": baseline_score,
            "repo_dir": repo_dir,
            "branch": optimization_branch,
            "status": "running",
        }

    async def _execute_workflow(
        self, workflow_id: str, workflow_data: dict[str, Any]
    ) -> None:
        """Execute the optimization workflow (main evolution loop).

        This mirrors the main loop from worker/src/worker/cli.py.
        """
        global _stop_generation
        
        try:
            generation = 0
            current_best_score = workflow_data["baseline_score"]
            max_generations = workflow_data["max_generations"]
            agents_per_generation = workflow_data["agents_per_generation"]
            parallel = workflow_data["parallel"]
            min_improvement_pct = workflow_data["min_improvement_pct"]
            early_stop = workflow_data["early_stop"]
            verbosity = workflow_data.get("verbosity", 1)
            step_count = 0
            total_improvements = 0
            total_attempts = 0
            repo_path = self.workspace_root / workflow_data["repo_dir"]

            while generation < max_generations and workflow_data["total_cost"] < workflow_data["total_cost_limit"]:
                # Check if workflow was paused/stopped
                workflow_key = f"optimization_workflow:{workflow_id}"
                current_data = await self.redis_client.get(workflow_key)
                if current_data:
                    status = json.loads(current_data).get("status")
                    if status in ("paused", "stopped"):
                        return

                generation += 1
                _stop_generation.clear()

                if verbosity >= 1:
                    logger.info(f"[OptimizationService] ═══ Generation {generation}/{max_generations} ═══")
                    logger.info(f"[OptimizationService] Current best score: {current_best_score}")

                # Spawn worker instances
                instances = await self._spawn_worker_instances(
                    workflow_id, generation, workflow_data, current_best_score
                )

                total_attempts += len(instances)
                workflow_data["total_attempts"] = total_attempts
                workflow_data["generation"] = generation
                await self._save_workflow_state(workflow_id, workflow_data)

                # Wait for workers to complete
                completed = await self._wait_for_workers(
                    workflow_id, instances, workflow_data["time_limit_seconds"],
                    early_stop, min_improvement_pct, current_best_score, verbosity
                )

                # Evaluate results
                evaluated = await self._evaluate_instances(workflow_id, completed, workflow_data)

                # Select best instance
                best = self._select_best_instance(evaluated, current_best_score, min_improvement_pct)

                if not best:
                    if verbosity >= 1:
                        logger.info(f"[OptimizationService] No significant improvement in generation {generation}")
                    continue

                # Apply improvement
                old_score = current_best_score
                current_best_score = best["evaluation_score"]
                step_count += 1
                total_improvements += 1
                
                _, improvement_pct = is_significant_improvement(old_score, current_best_score, min_improvement_pct)

                if verbosity >= 1:
                    logger.info(f"[OptimizationService] ✓ IMPROVED! {old_score:.2f} → {current_best_score:.2f} (+{improvement_pct:.1f}%)")

                # Save step snapshot
                save_step_snapshot(
                    source_path=repo_path,
                    output_dir=repo_path,
                    step_number=step_count,
                    agent_id=best["instance_id"],
                    baseline_score=old_score,
                    final_score=current_best_score,
                    improvement_pct=improvement_pct,
                    generation=generation,
                    console=None,
                )

                # Commit changes to user's repository
                commit_msg = f"Gen {generation} | {best['instance_id']}: +{improvement_pct:.1f}% ({old_score:.2f} → {current_best_score:.2f})"
                commit_result = self.github_service.commit_changes(
                    repo_dir=workflow_data["repo_dir"],
                    commit_message=commit_msg,
                    branch=workflow_data["branch"],
                )

                if commit_result.get("success"):
                    self.github_service.push_changes(
                        repo_dir=workflow_data["repo_dir"],
                        branch=workflow_data["branch"],
                    )

                # Update state
                workflow_data["current_best_score"] = current_best_score
                workflow_data["step_count"] = step_count
                workflow_data["total_improvements"] = total_improvements
                workflow_data["steps"].append({
                    "step": step_count,
                    "generation": generation,
                    "agent_id": best["instance_id"],
                    "baseline_score": old_score,
                    "final_score": current_best_score,
                    "improvement": current_best_score - old_score,
                    "improvement_percent": improvement_pct,
                    "timestamp": datetime.now().isoformat(),
                })
                
                await self._save_workflow_state(workflow_id, workflow_data)

            # Complete
            workflow_data["status"] = "completed"
            workflow_data["completed_at"] = datetime.now().isoformat()
            
            final_improvement = current_best_score - workflow_data["baseline_score"]
            final_pct = (final_improvement / workflow_data["baseline_score"] * 100) if workflow_data["baseline_score"] > 0 else 0
            workflow_data["improvement"] = final_improvement
            workflow_data["improvement_percent"] = final_pct

            if verbosity >= 1:
                logger.info(f"[OptimizationService] ══════════════════════════════════════════════════════════")
                logger.info(f"[OptimizationService] OPTIMIZATION COMPLETE!")
                logger.info(f"[OptimizationService] Initial: {workflow_data['baseline_score']:.2f} → Final: {current_best_score:.2f}")
                logger.info(f"[OptimizationService] Improvement: +{final_improvement:.2f} (+{final_pct:.1f}%)")
                logger.info(f"[OptimizationService] Successful: {total_improvements}/{total_attempts}")
                logger.info(f"[OptimizationService] ══════════════════════════════════════════════════════════")

            await self._save_workflow_state(workflow_id, workflow_data)

        except Exception as e:
            logger.error(f"[OptimizationService] Workflow failed: {e}", exc_info=True)
            workflow_data["status"] = "failed"
            workflow_data["error"] = str(e)
            await self._save_workflow_state(workflow_id, workflow_data)

    async def _spawn_worker_instances(
        self,
        workflow_id: str,
        generation: int,
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> list[dict[str, Any]]:
        """Spawn worker instances for the generation."""
        instances = []
        agent_types = workflow_data.get("agent_types", ["optimizer"])
        models = workflow_data["models"]
        total_agents = workflow_data["agents_per_generation"]

        # Distribute agents across models
        model_instances = []
        total_from_models = sum(m.get("instances", 0) for m in models)
        
        if total_from_models > 0:
            for model in models:
                for _ in range(model.get("instances", 0)):
                    model_instances.append(model)
        else:
            per_model = max(1, total_agents // len(models)) if models else 0
            for idx, model in enumerate(models):
                count = per_model + (1 if idx < (total_agents - per_model * len(models)) else 0)
                for _ in range(count):
                    model_instances.append(model)

        for i, model in enumerate(model_instances):
            agent_type = agent_types[i % len(agent_types)]
            instance_id = f"{workflow_id[:8]}-gen{generation}-{agent_type}-{i+1}"
            
            instance = {
                "instance_id": instance_id,
                "generation": generation,
                "model_provider": model["provider"],
                "model_name": model["model_name"],
                "api_key": model.get("api_key"),
                "agent_type": agent_type,
                "status": 1,  # in_progress
                "started_at": datetime.now().isoformat(),
            }
            instances.append(instance)

        # Spawn workers
        repo_path = self.workspace_root / workflow_data["repo_dir"]
        for instance in instances:
            asyncio.create_task(
                self._run_worker_instance(instance, str(repo_path), workflow_data, baseline_score)
            )

        return instances

    async def _run_worker_instance(
        self,
        instance: dict[str, Any],
        source_workspace: str,
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> None:
        """Run a single worker instance."""
        global _stop_generation
        
        try:
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
        except Exception as e:
            instance["error"] = str(e)
            instance["status"] = 2  # rejected
            instance["completed_at"] = datetime.now().isoformat()

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
                evaluator_path=workflow_data["evaluator_path"],
                agent_type=instance.get("agent_type", "optimizer"),
                agent_id=instance["instance_id"],
                baseline_score=baseline_score,
                task=workflow_data["user_prompt"],
                max_iterations=workflow_data["max_iterations_per_agent"],
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

            # Copy back changes if successful
            if workspace_manager and agent_result.success:
                try:
                    # Copy changes to source workspace
                    for item in workspace_manager.actual_root.iterdir():
                        if item.name not in (".git", "steps"):
                            dest = Path(source_workspace) / item.name
                            if item.is_dir():
                                if dest.exists():
                                    shutil.rmtree(dest)
                                shutil.copytree(item, dest)
                            else:
                                shutil.copy2(item, dest)
                    workspace_manager.cleanup()
                except Exception as e:
                    result["copy_error"] = str(e)

            return result

        finally:
            if api_key_env:
                if original_key is not None:
                    os.environ[api_key_env] = original_key
                elif api_key_env in os.environ:
                    del os.environ[api_key_env]

    async def _wait_for_workers(
        self,
        workflow_id: str,
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

        while time.time() - start_time < time_limit:
            completed = [i for i in instances if i.get("completed_at")]
            
            if len(completed) == len(instances):
                break

            # Check for early stop
            if early_stop and not _stop_generation.is_set():
                for inst in completed:
                    result = inst.get("worker_result", {})
                    if result.get("success") and result.get("score"):
                        is_sig, pct = is_significant_improvement(
                            current_best_score, result["score"], min_improvement_pct
                        )
                        if is_sig:
                            if verbosity >= 1:
                                logger.info(f"[OptimizationService] ⚡ Early stop: +{pct:.1f}%")
                            _stop_generation.set()
                            await asyncio.sleep(2)
                            break

            if _stop_generation.is_set():
                break

            await asyncio.sleep(1)

        return [i for i in instances if i.get("completed_at")]

    async def _evaluate_instances(
        self,
        workflow_id: str,
        instances: list[dict[str, Any]],
        workflow_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate completed instances."""
        for instance in instances:
            result = instance.get("worker_result", {})
            if result.get("success"):
                instance["evaluation_score"] = result.get("score")
            else:
                instance["evaluation_score"] = workflow_data["baseline_score"]
                instance["error"] = result.get("error")
        return instances

    def _select_best_instance(
        self,
        instances: list[dict[str, Any]],
        baseline_score: float,
        min_improvement_pct: float,
    ) -> dict[str, Any] | None:
        """Select the best significantly improved instance."""
        improved = []
        for inst in instances:
            score = inst.get("evaluation_score")
            if score and not inst.get("error"):
                is_sig, pct = is_significant_improvement(baseline_score, score, min_improvement_pct)
                if is_sig:
                    inst["_improvement_pct"] = pct
                    improved.append(inst)

        if not improved:
            return None

        improved.sort(key=lambda x: x["evaluation_score"], reverse=True)
        return improved[0]

    async def _save_workflow_state(
        self, workflow_id: str, workflow_data: dict[str, Any]
    ) -> None:
        """Save workflow state to Redis."""
        await self.connect()
        workflow_key = f"optimization_workflow:{workflow_id}"
        await self.redis_client.setex(workflow_key, 7200, json.dumps(workflow_data))

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """Get workflow status."""
        await self.connect()
        workflow_key = f"optimization_workflow:{workflow_id}"
        data = await self.redis_client.get(workflow_key)
        
        if not data:
            return None
        
        return json.loads(data)

    async def pause_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Pause an active workflow."""
        await self.connect()
        workflow_key = f"optimization_workflow:{workflow_id}"
        data = await self.redis_client.get(workflow_key)
        
        if not data:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = json.loads(data)
        if workflow.get("status") != "running":
            return {"success": False, "error": f"Workflow not running: {workflow.get('status')}"}
        
        workflow["status"] = "paused"
        workflow["paused_at"] = datetime.now().isoformat()
        await self.redis_client.setex(workflow_key, 7200, json.dumps(workflow))
        
        return {"success": True, "status": "paused"}

    async def resume_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Resume a paused workflow."""
        await self.connect()
        workflow_key = f"optimization_workflow:{workflow_id}"
        data = await self.redis_client.get(workflow_key)
        
        if not data:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = json.loads(data)
        if workflow.get("status") != "paused":
            return {"success": False, "error": f"Workflow not paused: {workflow.get('status')}"}
        
        workflow["status"] = "running"
        await self.redis_client.setex(workflow_key, 7200, json.dumps(workflow))
        
        asyncio.create_task(self._execute_workflow(workflow_id, workflow))
        
        return {"success": True, "status": "running"}

    async def stop_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Stop a workflow completely."""
        await self.connect()
        workflow_key = f"optimization_workflow:{workflow_id}"
        data = await self.redis_client.get(workflow_key)
        
        if not data:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = json.loads(data)
        workflow["status"] = "stopped"
        workflow["stopped_at"] = datetime.now().isoformat()
        await self.redis_client.setex(workflow_key, 7200, json.dumps(workflow))
        
        return {
            "success": True,
            "status": "stopped",
            "final_score": workflow.get("current_best_score"),
        }
