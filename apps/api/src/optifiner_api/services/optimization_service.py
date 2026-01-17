"""Optimization workflow service for orchestrating multi-model code optimization.

This service mirrors the functionality of worker/src/worker/cli.py, providing:
- Baseline evaluation
- Multi-agent optimization with configurable models
- Minimum improvement threshold to filter noise
- Step snapshots for tracking evolution history
- Early stopping when improvement found
"""

import asyncio
import json
import logging
import os
import shutil
import sys
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


def is_significant_improvement(
    baseline_score: float,
    new_score: float,
    min_improvement_pct: float = 3.0
) -> tuple[bool, float]:
    """Check if an improvement is statistically significant (above noise threshold).
    
    Small improvements (e.g., 0.01%) are likely just benchmark instability/noise.
    This function filters out noise by requiring a minimum percentage improvement.
    
    This mirrors the function from worker/src/worker/cli.py.
    
    Args:
        baseline_score: The original score to compare against.
        new_score: The new score after changes.
        min_improvement_pct: Minimum improvement percentage required (default 3%).
    
    Returns:
        Tuple of (is_significant, improvement_percent).
    """
    if baseline_score <= 0:
        # Can't calculate percentage improvement with zero/negative baseline
        return new_score > baseline_score, 0.0
    
    improvement_pct = ((new_score - baseline_score) / baseline_score) * 100
    is_significant = improvement_pct >= min_improvement_pct
    return is_significant, improvement_pct


def save_step_snapshot(
    source_path: Path,
    output_dir: Path,
    step_number: int,
    agent_id: str,
    baseline_score: float,
    final_score: float,
    improvement_pct: float,
    generation: int,
) -> Path:
    """Save a snapshot of the codebase at a specific evolution step.
    
    Creates a folder like: output_dir/steps/step_001/
    With the codebase and a metadata.json file.
    
    This mirrors the function from worker/src/worker/cli.py.
    
    Args:
        source_path: Path to the current codebase to snapshot.
        output_dir: Base output directory.
        step_number: The step number (1-indexed).
        agent_id: ID of the agent that made this improvement.
        baseline_score: Score before this improvement.
        final_score: Score after this improvement.
        improvement_pct: Percentage improvement.
        generation: Current generation number.
        
    Returns:
        Path to the created step folder.
    """
    # Create steps directory structure
    steps_dir = output_dir / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    
    # Create step folder with zero-padded number
    step_folder = steps_dir / f"step_{step_number:03d}"
    
    # Copy codebase to step folder
    if step_folder.exists():
        shutil.rmtree(step_folder)
    
    # Copy source (excluding .git and steps folder to avoid recursion)
    def ignore_patterns(directory, files):
        ignored = []
        if Path(directory) == source_path:
            if ".git" in files:
                ignored.append(".git")
            if "steps" in files:
                ignored.append("steps")
        elif ".git" in files:
            ignored.append(".git")
        return ignored
    
    shutil.copytree(source_path, step_folder, ignore=ignore_patterns)
    
    # Create metadata file
    metadata = {
        "step": step_number,
        "generation": generation,
        "agent_id": agent_id,
        "baseline_score": baseline_score,
        "final_score": final_score,
        "improvement": final_score - baseline_score,
        "improvement_percent": improvement_pct,
        "timestamp": datetime.now().isoformat(),
    }
    
    metadata_path = step_folder / "step_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"[OptimizationService] Saved step {step_number} snapshot to: {step_folder.name}/")
    
    return step_folder


def save_initial_snapshot(
    source_path: Path,
    output_dir: Path,
    baseline_score: float,
) -> Path:
    """Save the initial (step 0) snapshot before any evolution.
    
    This mirrors the function from worker/src/worker/cli.py.
    
    Args:
        source_path: Path to the initial codebase.
        output_dir: Base output directory.
        baseline_score: Initial baseline score.
        
    Returns:
        Path to the created step_000 folder.
    """
    steps_dir = output_dir / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    
    step_folder = steps_dir / "step_000"
    
    if step_folder.exists():
        shutil.rmtree(step_folder)
    
    # Copy source (excluding .git and steps folder)
    def ignore_patterns(directory, files):
        ignored = []
        if Path(directory) == source_path:
            if ".git" in files:
                ignored.append(".git")
            if "steps" in files:
                ignored.append("steps")
        elif ".git" in files:
            ignored.append(".git")
        return ignored
    
    shutil.copytree(source_path, step_folder, ignore=ignore_patterns)
    
    # Create metadata file
    metadata = {
        "step": 0,
        "generation": 0,
        "agent_id": "initial",
        "baseline_score": baseline_score,
        "final_score": baseline_score,
        "improvement": 0.0,
        "improvement_percent": 0.0,
        "timestamp": datetime.now().isoformat(),
        "is_initial": True,
    }
    
    metadata_path = step_folder / "step_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"[OptimizationService] Saved initial snapshot to: {steps_dir.name}/step_000/")
    
    return step_folder

# Import worker functions from services/worker
# First try importing from installed package (if worker was installed via pip install -e)
# Then fall back to adding worker source to path for development
try:
    from worker.cli import run_evaluator, copy_workspace, run_single_agent_isolated
except ImportError:
    # Fallback: add worker source to path for development
    # Calculate path to worker source relative to this file
    # File is at: apps/api/src/optifiner_api/services/optimization_service.py
    # Worker is at: services/worker/src/worker/
    _worker_src_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "worker" / "src"
    if _worker_src_path.exists() and str(_worker_src_path) not in sys.path:
        sys.path.insert(0, str(_worker_src_path))
    
    # Try importing again after adding to path
    try:
        from worker.cli import run_evaluator, copy_workspace, run_single_agent_isolated
    except ImportError as e:
        # Final fallback if worker modules aren't available
        import warnings
        warnings.warn(
            f"Failed to import worker functions: {e}. "
            f"Worker functionality will be limited. "
            f"To fix: run 'pip install -e ../../services/worker' from apps/api/ or run setup_worker_link.sh"
        )
        run_evaluator = None
        copy_workspace = None
        run_single_agent_isolated = None

# Thread pool for running worker instances (blocking operations)
_executor = ThreadPoolExecutor(max_workers=10)


class OptimizationService:
    """Service for orchestrating optimization workflows."""

    def __init__(self):
        """Initialize optimization service."""
        self.redis_client: redis.Redis | None = None
        self.github_service = GitHubService()
        # Resolve workspace root path (same logic as GitHubService)
        workspace_path = settings.WORKER_WORKSPACE_PATH
        if not Path(workspace_path).is_absolute():
            # File is at: apps/api/src/optifiner_api/services/optimization_service.py
            # Project root is 6 levels up: services -> optifiner_api -> src -> api -> apps -> project_root
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            self.workspace_root = project_root / workspace_path
        else:
            self.workspace_root = Path(workspace_path)
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

        Uses the existing run_evaluator function from worker.cli if available.
        If evaluator_path is None, the evaluation may discover/create the evaluator.

        Args:
            evaluator_path: Path to the evaluator script (None if not yet discovered)
            workspace: Path to the workspace to evaluate
            timeout: Timeout in seconds

        Returns:
            Tuple of (score, error, data). If successful, error is None.
        """
        logger.debug(f"[OptimizationService] _run_evaluator called: evaluator_path={evaluator_path}, workspace={workspace}, timeout={timeout}")
        
        # Ensure workspace path is absolute
        workspace_path = Path(workspace)
        if not workspace_path.is_absolute():
            workspace_path = self.workspace_root / workspace_path.relative_to(settings.WORKER_WORKSPACE_PATH) if str(workspace_path).startswith(settings.WORKER_WORKSPACE_PATH) else self.workspace_root / workspace
        workspace = str(workspace_path.resolve())
        logger.debug(f"[OptimizationService] Resolved workspace path: {workspace} (exists={workspace_path.exists()})")
        
        if not workspace_path.exists():
            error_msg = f"Workspace not found: {workspace}"
            logger.error(f"[OptimizationService] {error_msg}")
            return None, error_msg, None
        
        if run_evaluator is not None:
            # Use existing worker function
            logger.debug(f"[OptimizationService] Using run_evaluator from worker.cli")
            try:
                # If evaluator_path is None or empty, check for optifiner_benchmark.py in workspace
                if not evaluator_path:
                    benchmark_path = workspace_path / "optifiner_benchmark.py"
                    if benchmark_path.exists():
                        evaluator_path = str(benchmark_path)
                        logger.debug(f"[OptimizationService] Found optifiner_benchmark.py: {evaluator_path}")
                    else:
                        error_msg = "No evaluator path provided and optifiner_benchmark.py not found in workspace"
                        logger.error(f"[OptimizationService] {error_msg}")
                        return None, error_msg, None
                
                # Ensure evaluator path is absolute if it's relative
                eval_path_obj = Path(evaluator_path)
                if not eval_path_obj.is_absolute():
                    # Try relative to workspace first
                    eval_path_obj = workspace_path / evaluator_path
                    if not eval_path_obj.exists():
                        # Try relative to workspace root
                        eval_path_obj = self.workspace_root / evaluator_path
                evaluator_path = str(eval_path_obj.resolve())
                logger.debug(f"[OptimizationService] Resolved evaluator path: {evaluator_path} (exists={eval_path_obj.exists()})")
                
                if not eval_path_obj.exists():
                    error_msg = f"Evaluator path does not exist: {evaluator_path}"
                    logger.error(f"[OptimizationService] {error_msg}")
                    return None, error_msg, None
                
                result = run_evaluator(evaluator_path, workspace, timeout, return_full_data=True)
                score, error, data = result
                logger.debug(f"[OptimizationService] run_evaluator returned: score={score}, error={error}")
                
                # Log evaluation values
                if score is not None:
                    logger.info(f"[OptimizationService] Evaluation result - Score: {score}")
                    if data:
                        logger.info(f"[OptimizationService] Evaluation data: {json.dumps(data, indent=2)}")
                elif error:
                    logger.warning(f"[OptimizationService] Evaluation error: {error}")
                
                return result
            except Exception as e:
                error_msg = f"Error running evaluator: {e}"
                logger.error(f"[OptimizationService] {error_msg}", exc_info=True)
                return None, error_msg, None
        else:
            # Fallback implementation
            error_msg = "Worker functions not available - cannot run evaluator"
            logger.error(f"[OptimizationService] {error_msg}")
            return None, error_msg, None

    def _find_evaluator(self, repo_dir: str) -> str | None:
        """Find evaluator script in repository.

        Args:
            repo_dir: Directory name of the repository

        Returns:
            Path to evaluator script or None
        """
        logger.debug(f"[OptimizationService] _find_evaluator called: repo_dir={repo_dir}")
        repo_path = self.workspace_root / repo_dir
        logger.debug(f"[OptimizationService] Searching in repo_path: {repo_path} (exists={repo_path.exists()})")

        # Common evaluator names
        evaluator_names = ["evaluate.py", "evaluator.py", "evaluate.sh", "evaluator.sh"]
        logger.debug(f"[OptimizationService] Checking common evaluator names: {evaluator_names}")

        for name in evaluator_names:
            evaluator_path = repo_path / name
            logger.debug(f"[OptimizationService] Checking: {evaluator_path} (exists={evaluator_path.exists()})")
            if evaluator_path.exists():
                logger.debug(f"[OptimizationService] Found evaluator: {evaluator_path}")
                return str(evaluator_path)

        # Search for any file with "evaluat" in the name
        logger.debug(f"[OptimizationService] Searching recursively for files with 'evaluat' in name")
        for file_path in repo_path.rglob("*evaluat*"):
            if file_path.is_file() and file_path.suffix in [".py", ".sh", ".js"]:
                logger.debug(f"[OptimizationService] Found evaluator: {file_path}")
                return str(file_path)

        logger.debug(f"[OptimizationService] No evaluator found in {repo_path}")
        return None

    async def start_optimization_workflow(
        self,
        repo_url: str,
        branch: str | None,
        total_cost_limit: float,
        models: list[dict[str, Any]],
        user_prompt: str,
        evaluator_path: str | None,
        max_iterations_per_agent: int,
        time_limit_seconds: int,
        min_improvement_pct: float = 6.0,
        early_stop: bool = True,
    ) -> dict[str, Any]:
        """Start an optimization workflow.
        
        This mirrors the functionality of worker/src/worker/cli.py main() function.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone
            total_cost_limit: Total cost limit
            models: List of model configurations
            user_prompt: User prompt
            evaluator_path: Optional path to evaluator script
            max_iterations_per_agent: Max iterations per agent
            time_limit_seconds: Time limit per generation
            min_improvement_pct: Minimum improvement percentage to accept (default 6.0%, filters noise)
            early_stop: Stop generation early when improvement found (default True)

        Returns:
            Dictionary with workflow information
        """
        logger.debug(f"[OptimizationService] start_optimization_workflow called: repo_url={repo_url}, branch={branch}, models={len(models)}")
        
        logger.debug(f"[OptimizationService] Connecting to Redis")
        await self.connect()

        workflow_id = str(uuid.uuid4())
        logger.info(f"[OptimizationService] Created workflow_id: {workflow_id}")

        # Clone repository
        logger.debug(f"[OptimizationService] Cloning repository: {repo_url}, branch={branch}")
        clone_result = self.github_service.clone_repository(
            repo_url=repo_url,
            branch=branch,
            target_dir=None,  # Use default repo name
        )
        logger.debug(f"[OptimizationService] clone_repository result: success={clone_result.get('success')}, repo_name={clone_result.get('repo_name')}")

        if not clone_result.get("success"):
            error = f"Failed to clone repository: {clone_result.get('error')}"
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }

        repo_dir = clone_result.get("repo_name")
        if not repo_dir:
            error = "Failed to determine repository directory"
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }
        logger.debug(f"[OptimizationService] Repository directory: {repo_dir}")

        # Create a new branch for optimization workflow
        # Use workflow_id to create a unique branch name
        optimization_branch_name = f"optifiner-{workflow_id[:8]}"
        logger.debug(f"[OptimizationService] Creating optimization branch: {optimization_branch_name}")
        
        # Get the cloned branch (use the branch that was actually cloned)
        cloned_branch = clone_result.get("branch")
        logger.debug(f"[OptimizationService] Cloned branch: {cloned_branch}")
        
        branch_result = self.github_service.create_branch(
            repo_dir=repo_dir,
            branch_name=optimization_branch_name,
            from_branch=cloned_branch,  # Create from the cloned branch
        )
        logger.debug(f"[OptimizationService] create_branch result: success={branch_result.get('success')}, branch={branch_result.get('branch')}")

        if not branch_result.get("success"):
            error = f"Failed to create optimization branch: {branch_result.get('error')}"
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }

        # Use the optimization branch for all commits
        optimization_branch = branch_result.get("branch", optimization_branch_name)
        logger.debug(f"[OptimizationService] Using optimization branch: {optimization_branch}")

        # Run baseline evaluation first - this may create/discover the evaluator
        repo_path = self.workspace_root / repo_dir
        logger.debug(f"[OptimizationService] Running baseline evaluation: evaluator_path={evaluator_path}, workspace={repo_path} (exists={repo_path.exists()})")
        
        if not repo_path.exists():
            error = f"Repository workspace not found: {repo_path}. Expected at: {self.workspace_root}/{repo_dir}"
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }
        
        # Try to run baseline evaluation - evaluator_path may be None initially
        # The evaluation process may discover/create the evaluator
        baseline_score = None
        baseline_error = None
        baseline_data = None
        
        if evaluator_path:
            # Evaluator provided - verify it exists and run
            evaluator_path_obj = Path(evaluator_path)
            if not evaluator_path_obj.is_absolute():
                # Resolve relative to repo
                evaluator_path_obj = repo_path / evaluator_path
            
            if evaluator_path_obj.exists():
                logger.debug(f"[OptimizationService] Running baseline with provided evaluator: {evaluator_path_obj}")
                baseline_score, baseline_error, baseline_data = self._run_evaluator(
                    str(evaluator_path_obj), str(repo_path)
                )
            else:
                baseline_error = f"Provided evaluator path does not exist: {evaluator_path_obj}"
                logger.error(f"[OptimizationService] {baseline_error}")
        else:
            # No evaluator provided - skip search and directly run benchmark builder to create one
            # The benchmark builder will create optifiner_benchmark.py
            logger.debug(f"[OptimizationService] No evaluator provided, skipping search and running benchmark builder directly")
            
            # Check if we can import benchmark builder
            try:
                from worker.benchmark_builder import run_benchmark_builder
                from worker.config import ModelConfig, ModelProvider
                from worker.workspace import WorkspaceManager, set_workspace
                from worker.observability import AgentObserver, set_observer, get_observer
                from worker.tools.evaluate import set_benchmark_dev_mode
                
                # Use the first model from the request to run benchmark builder
                # If no models provided, use a default
                if models and len(models) > 0:
                    builder_model = models[0]
                    builder_provider = builder_model.get("provider", "google")
                    builder_model_name = builder_model.get("model_name", "gemini-2.0-flash-exp")
                    builder_api_key = builder_model.get("api_key")
                else:
                    builder_provider = "google"
                    builder_model_name = "gemini-2.0-flash-exp"
                    builder_api_key = None
                
                logger.info(f"[OptimizationService] Running benchmark builder with {builder_provider}/{builder_model_name}")
                
                # Set API key in environment if provided
                provider_key_map = {
                    "anthropic": "ANTHROPIC_API_KEY",
                    "google": "GOOGLE_API_KEY",
                    "openai": "OPENAI_API_KEY",
                }
                api_key_env = provider_key_map.get(builder_provider)
                original_key = None
                if api_key_env and builder_api_key:
                    original_key = os.environ.get(api_key_env)
                    os.environ[api_key_env] = builder_api_key
                
                try:
                    # Create workspace manager for benchmark builder
                    workspace_manager = WorkspaceManager(workspace_id="benchmark-builder")
                    workspace_manager.setup(repo_path)
                    set_workspace(workspace_manager)
                    
                    # Set up observer
                    observer = AgentObserver(verbosity=0, console=None)
                    set_observer(observer)
                    
                    # Configure model
                    model_timeout = 50.0 if "gemini" in builder_model_name.lower() and "flash" in builder_model_name.lower() else 60.0
                    model_config = ModelConfig(
                        provider=ModelProvider(builder_provider),
                        model_name=builder_model_name,
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
                    
                    if success:
                        # Check if benchmark was created
                        benchmark_path = repo_path / "optifiner_benchmark.py"
                        if benchmark_path.exists():
                            evaluator_path = str(benchmark_path)
                            logger.info(f"[OptimizationService] Benchmark builder created evaluator: {evaluator_path}")
                            
                            # Now run baseline with the created evaluator
                            baseline_score, baseline_error, baseline_data = self._run_evaluator(
                                evaluator_path, str(repo_path)
                            )
                        else:
                            baseline_error = f"Benchmark builder succeeded but optifiner_benchmark.py not found: {message}"
                            logger.error(f"[OptimizationService] {baseline_error}")
                    else:
                        baseline_error = f"Benchmark builder failed: {message}"
                        logger.error(f"[OptimizationService] {baseline_error}")
                    
                    # Cleanup
                    workspace_manager.cleanup()
                    set_workspace(None)
                    set_observer(None)
                    
                finally:
                    # Restore original API key
                    if api_key_env:
                        if original_key is not None:
                            os.environ[api_key_env] = original_key
                        elif api_key_env in os.environ:
                            del os.environ[api_key_env]
            
            except ImportError as e:
                logger.warning(f"[OptimizationService] Benchmark builder not available: {e}")
                baseline_error = "No evaluator found and benchmark builder not available. Please provide evaluator_path or ensure the repository contains an evaluator script."
            except Exception as e:
                logger.error(f"[OptimizationService] Error running benchmark builder: {e}", exc_info=True)
                baseline_error = f"Failed to run benchmark builder: {e}"
        
        logger.debug(f"[OptimizationService] Baseline evaluation result: score={baseline_score}, error={baseline_error}")

        if baseline_error:
            error = f"Baseline evaluation failed: {baseline_error}"
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }

        if baseline_score is None:
            error = "Baseline evaluation did not return a score"
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }
        
        # Log baseline evaluation values (cli.py style)
        logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
        logger.info(f"[OptimizationService] BASELINE EVALUATION COMPLETE")
        logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
        logger.info(f"[OptimizationService] Baseline Score: {baseline_score}")
        logger.info(f"[OptimizationService] Minimum Improvement Threshold: {min_improvement_pct}% (filters noise)")
        logger.info(f"[OptimizationService] Early Stop: {early_stop}")
        if baseline_data:
            if "fps" in baseline_data:
                logger.info(f"[OptimizationService]   FPS: {baseline_data['fps']:.2f}")
            if baseline_data.get("tests_passed") is not None and baseline_data.get("tests_total") is not None:
                logger.info(f"[OptimizationService]   Tests: {baseline_data['tests_passed']}/{baseline_data['tests_total']}")
            if baseline_data.get("metrics"):
                for k, v in baseline_data["metrics"].items():
                    if k not in ("fps",):
                        logger.info(f"[OptimizationService]   {k}: {v}")
        logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
        
        # After baseline evaluation, ensure we have evaluator_path for future use
        if not evaluator_path:
            logger.debug(f"[OptimizationService] Finding evaluator after baseline evaluation")
            evaluator_path = self._find_evaluator(repo_dir)
            if not evaluator_path:
                # Check for optifiner_benchmark.py which might have been created
                benchmark_path = repo_path / "optifiner_benchmark.py"
                if benchmark_path.exists():
                    evaluator_path = str(benchmark_path)
                    logger.info(f"[OptimizationService] Found evaluator created by baseline: {evaluator_path}")
        
        if not evaluator_path:
            error = "Evaluator script not found in repository and not provided. Baseline evaluation completed but no evaluator path could be determined."
            logger.error(f"[OptimizationService] {error}")
            return {
                "success": False,
                "error": error,
            }
        
        logger.info(f"[OptimizationService] Baseline evaluation successful: score={baseline_score}, evaluator_path={evaluator_path}")
        
        # Save initial snapshot (step 0) - mirrors cli.py behavior
        save_initial_snapshot(repo_path, repo_path, baseline_score)
        
        # Store workflow state
        workflow_key = f"optimization_workflow:{workflow_id}"
        workflow_data = {
            "workflow_id": workflow_id,
            "status": "running",
            "repo_url": repo_url,
            "repo_dir": repo_dir,
            "branch": optimization_branch,  # Use the optimization branch we created
            "original_branch": branch,  # Keep track of original branch
            "baseline_score": baseline_score,
            "baseline_data": baseline_data or {},
            "current_best_score": baseline_score,
            "generation": 0,
            "total_cost_limit": total_cost_limit,
            "total_cost": 0.0,
            "models": models,
            "user_prompt": user_prompt,
            "evaluator_path": evaluator_path,
            "max_iterations_per_agent": max_iterations_per_agent,
            "time_limit_seconds": time_limit_seconds,
            "min_improvement_pct": min_improvement_pct,  # Noise threshold
            "early_stop": early_stop,  # Early stopping flag
            "worker_instances": [],
            "started_at": time.time(),
            "total_generations": 0,
            "last_improvement_generation": None,
            "accepted_layers_count": 0,
            "accepted_generations": [],  # List of generation numbers that were accepted
            "step_count": 0,  # Track total successful steps across all generations
            "graph_data": {
                "nodes": [
                    {
                        "id": "baseline",
                        "type": "baseline",
                        "generation": 0,
                        "score": baseline_score,
                        "instance_id": None,
                    }
                ],
                "edges": [],
            },
            "parent_instance_id": None,  # Parent instance for next generation
        }

        await self.redis_client.setex(
            workflow_key, 7200, json.dumps(workflow_data)
        )  # 2 hour TTL

        # Start workflow execution in background
        asyncio.create_task(
            self._execute_workflow(workflow_id, workflow_data)
        )

        return {
            "success": True,
            "workflow_id": workflow_id,
            "baseline_score": baseline_score,
            "repo_dir": repo_dir,
            "branch": optimization_branch,  # Return the optimization branch
            "status": "running",
        }

    async def _execute_workflow(
        self, workflow_id: str, workflow_data: dict[str, Any]
    ) -> None:
        """Execute the optimization workflow.
        
        This mirrors the main loop from worker/src/worker/cli.py.

        Args:
            workflow_id: Workflow identifier
            workflow_data: Initial workflow data
        """
        try:
            generation = workflow_data.get("generation", 0)
            current_best_score = workflow_data.get("current_best_score", workflow_data["baseline_score"])
            total_cost = workflow_data.get("total_cost", 0.0)
            parent_instance_id = workflow_data.get("parent_instance_id", None)
            min_improvement_pct = workflow_data.get("min_improvement_pct", 6.0)
            early_stop = workflow_data.get("early_stop", True)
            step_count = workflow_data.get("step_count", 0)

            while total_cost < workflow_data["total_cost_limit"]:
                # Check if workflow was paused or stopped
                workflow_key = f"optimization_workflow:{workflow_id}"
                current_data = await self.redis_client.get(workflow_key)
                if current_data:
                    current_status = json.loads(current_data).get("status")
                    if current_status in ("paused", "stopped"):
                        return  # Exit execution loop
                
                generation += 1
                workflow_data["generation"] = generation
                workflow_data["parent_instance_id"] = parent_instance_id
                
                # Log generation header (cli.py style)
                logger.info(f"[OptimizationService] ")
                logger.info(f"[OptimizationService] ═══ Generation {generation} ═══")
                logger.info(f"[OptimizationService] Current best score: {current_best_score}")
                logger.info(f"[OptimizationService] Min improvement threshold: {min_improvement_pct}%")
                
                # Save workflow state with current generation before starting
                await self._save_workflow_state(workflow_id, workflow_data)

                # Spawn worker instances with parent tracking
                total_agents = sum(m.get("instances", 1) for m in workflow_data["models"])
                logger.info(f"[OptimizationService] Running {total_agents} agents...")
                
                worker_instances = await self._spawn_worker_instances(
                    workflow_id, generation, workflow_data, current_best_score, parent_instance_id
                )

                workflow_data["worker_instances"] = worker_instances
                
                # Save state after spawning instances
                await self._save_workflow_state(workflow_id, workflow_data)

                # Wait for workers to complete or time limit (with early stop support)
                completed_instances = await self._wait_for_workers(
                    workflow_id, worker_instances, workflow_data["time_limit_seconds"],
                    early_stop=early_stop, min_improvement_pct=min_improvement_pct,
                    current_best_score=current_best_score
                )

                # Evaluate all completed instances
                evaluated_instances = await self._evaluate_instances(
                    workflow_id, completed_instances, workflow_data
                )

                # Select best instance (only consider instances that significantly improve over current best)
                # This mirrors cli.py's is_significant_improvement check
                best_instance = self._select_best_instance(
                    evaluated_instances, current_best_score, min_improvement_pct
                )

                if not best_instance:
                    # No significant improvement, stop
                    logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
                    logger.info(f"[OptimizationService] NO SIGNIFICANT IMPROVEMENT (Generation {generation})")
                    logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
                    logger.info(f"[OptimizationService] Current Best Score: {current_best_score:.4f}")
                    logger.info(f"[OptimizationService] Baseline Score: {workflow_data['baseline_score']:.4f}")
                    logger.info(f"[OptimizationService] Total Improvement: {current_best_score - workflow_data['baseline_score']:.4f}")
                    logger.info(f"[OptimizationService] Min Improvement Threshold: {min_improvement_pct}%")
                    logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
                    
                    workflow_data["status"] = "completed"
                    workflow_data["message"] = f"No significant improvement (>{min_improvement_pct}%) found at generation {generation}, stopping workflow"
                    workflow_data["final_generation"] = generation
                    break

                # Update best score and step count
                old_best_score = current_best_score
                current_best_score = best_instance["evaluation_score"]
                workflow_data["current_best_score"] = current_best_score
                workflow_data["last_improvement_generation"] = generation
                step_count += 1
                workflow_data["step_count"] = step_count
                
                # Log improvement (cli.py style)
                improvement = current_best_score - old_best_score
                _, improvement_pct = is_significant_improvement(old_best_score, current_best_score, min_improvement_pct)
                total_improvement = current_best_score - workflow_data["baseline_score"]
                total_improvement_pct = (total_improvement / workflow_data["baseline_score"] * 100) if workflow_data["baseline_score"] > 0 else 0
                
                logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
                logger.info(f"[OptimizationService] ✓ AGENT IMPROVED! (Generation {generation}, Step {step_count})")
                logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
                logger.info(f"[OptimizationService] Instance ID: {best_instance['instance_id']}")
                logger.info(f"[OptimizationService] Model: {best_instance.get('model_provider')}/{best_instance.get('model_name')}")
                logger.info(f"[OptimizationService] Score: {old_best_score:.2f} → {current_best_score:.2f} (+{improvement_pct:.1f}%)")
                logger.info(f"[OptimizationService] Total from Baseline: {workflow_data['baseline_score']:.2f} → {current_best_score:.2f} (+{total_improvement_pct:.1f}%)")
                if best_instance.get("evaluation_data"):
                    eval_data = best_instance["evaluation_data"]
                    if "fps" in eval_data:
                        logger.info(f"[OptimizationService]   FPS: {eval_data['fps']:.2f}")
                    if eval_data.get("tests_passed") is not None and eval_data.get("tests_total") is not None:
                        logger.info(f"[OptimizationService]   Tests: {eval_data['tests_passed']}/{eval_data['tests_total']}")
                    if eval_data.get("metrics"):
                        for k, v in eval_data["metrics"].items():
                            if k not in ("fps",):
                                logger.info(f"[OptimizationService]   {k}: {v}")
                logger.info(f"[OptimizationService] ═══════════════════════════════════════════════════")
                
                # Save step snapshot (mirrors cli.py)
                repo_path = self.workspace_root / workflow_data["repo_dir"]
                save_step_snapshot(
                    source_path=repo_path,
                    output_dir=repo_path,
                    step_number=step_count,
                    agent_id=best_instance["instance_id"],
                    baseline_score=old_best_score,
                    final_score=current_best_score,
                    improvement_pct=improvement_pct,
                    generation=generation,
                )

                # Increment accepted layers count (this generation resulted in an accepted improvement)
                workflow_data["accepted_layers_count"] = workflow_data.get("accepted_layers_count", 0) + 1
                if "accepted_generations" not in workflow_data:
                    workflow_data["accepted_generations"] = []
                workflow_data["accepted_generations"].append(generation)

                # Update instance statuses and update graph node statuses
                graph_data = workflow_data.get("graph_data", {"nodes": [], "edges": []})
                
                for instance in evaluated_instances:
                    # Find and update the corresponding graph node
                    node = None
                    for n in graph_data["nodes"]:
                        if n.get("id") == instance["instance_id"]:
                            node = n
                            break
                    
                    if node is None:
                        # Node should exist, but create it if missing (fallback)
                        node = {
                            "id": instance["instance_id"],
                            "type": "unknown",
                            "generation": generation,
                            "score": None,
                            "instance_id": instance["instance_id"],
                            "model_provider": instance.get("model_provider"),
                            "model_name": instance.get("model_name"),
                        }
                        graph_data["nodes"].append(node)
                    
                    if instance["instance_id"] == best_instance["instance_id"]:
                        instance["status"] = 0  # accepted
                        instance["accepted_at_generation"] = generation
                        
                        # Update node status to accepted
                        node["type"] = "accepted"
                        node["score"] = instance["evaluation_score"]
                        
                        # Update parent for next generation
                        parent_instance_id = instance["instance_id"]
                        workflow_data["parent_instance_id"] = parent_instance_id
                    else:
                        instance["status"] = 2  # rejected
                        instance["rejected_at_generation"] = generation
                        
                        # Update node status to rejected
                        node["type"] = "rejected"
                        node["score"] = instance.get("evaluation_score")
                
                workflow_data["graph_data"] = graph_data

                # Commit and push changes from best instance
                await self._commit_and_push_best_instance(
                    workflow_id, best_instance, workflow_data
                )

                # Update code context (copy best instance workspace to main)
                await self._update_code_context(
                    workflow_id, best_instance, workflow_data
                )

                # Update workflow data
                workflow_data["worker_instances"] = evaluated_instances
                workflow_data["total_cost"] = total_cost  # TODO: Calculate actual cost
                workflow_data["total_generations"] = generation

                # Save workflow state after each generation completes
                await self._save_workflow_state(workflow_id, workflow_data)

            # Mark workflow as completed and log final summary (cli.py style)
            workflow_data["status"] = "completed"
            workflow_data["final_generation"] = generation
            workflow_data["total_generations"] = generation
            workflow_data["step_count"] = step_count
            
            # Final summary (cli.py style)
            final_improvement = current_best_score - workflow_data["baseline_score"]
            final_improvement_pct = (final_improvement / workflow_data["baseline_score"] * 100) if workflow_data["baseline_score"] > 0 else 0
            repo_path = self.workspace_root / workflow_data["repo_dir"]
            steps_dir = repo_path / "steps"
            
            logger.info(f"[OptimizationService] ")
            logger.info(f"[OptimizationService] ══════════════════════════════════════════════════════════")
            logger.info(f"[OptimizationService] OPTIMIZATION COMPLETE!")
            logger.info(f"[OptimizationService] ══════════════════════════════════════════════════════════")
            logger.info(f"[OptimizationService] Initial score: {workflow_data['baseline_score']}")
            logger.info(f"[OptimizationService] Final score: {current_best_score}")
            logger.info(f"[OptimizationService] Total improvement: +{final_improvement:.2f} (+{final_improvement_pct:.1f}%)")
            logger.info(f"[OptimizationService] ")
            logger.info(f"[OptimizationService] Successful improvements: {workflow_data.get('accepted_layers_count', 0)}/{generation}")
            logger.info(f"[OptimizationService] ")
            logger.info(f"[OptimizationService] Output location: {repo_path}")
            logger.info(f"[OptimizationService] Version history: {steps_dir} ({step_count + 1} snapshots)")
            logger.info(f"[OptimizationService] ══════════════════════════════════════════════════════════")
            
            await self._save_workflow_state(workflow_id, workflow_data)

        except Exception as e:
            logger.error(f"[OptimizationService] Workflow execution failed: {e}", exc_info=True)
            workflow_data["status"] = "failed"
            workflow_data["error"] = str(e)
            await self._save_workflow_state(workflow_id, workflow_data)

    async def _spawn_worker_instances(
        self,
        workflow_id: str,
        generation: int,
        workflow_data: dict[str, Any],
        baseline_score: float,
        parent_instance_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Spawn worker instances for all models.

        Args:
            workflow_id: Workflow identifier
            generation: Current generation number
            workflow_data: Workflow data
            baseline_score: Current baseline score
            parent_instance_id: Parent instance ID that spawned this generation

        Returns:
            List of worker instance dictionaries
        """
        instances = []

        for model_idx, model_config in enumerate(workflow_data["models"]):
            num_instances = model_config.get("instances", 1)

            for instance_idx in range(num_instances):
                instance_id = f"{workflow_id}-gen{generation}-{model_config['provider']}-{model_config['model_name']}-{instance_idx}"

                instance = {
                    "instance_id": instance_id,
                    "workflow_id": workflow_id,
                    "generation": generation,
                    "parent_instance_id": parent_instance_id,  # Track parent for graph
                    "model_provider": model_config["provider"],
                    "model_name": model_config["model_name"],
                    "api_key": model_config["api_key"],
                    "status": 1,  # in_progress
                    "evaluation_score": None,
                    "started_at": time.time(),
                    "completed_at": None,
                    "error": None,
                }

                instances.append(instance)

                # Add node to graph immediately when worker is created
                graph_data = workflow_data.get("graph_data", {"nodes": [], "edges": []})
                graph_data["nodes"].append({
                    "id": instance_id,
                    "type": "in_progress",  # Initial status, will be updated after evaluation
                    "generation": generation,
                    "score": None,  # Will be updated after evaluation
                    "instance_id": instance_id,
                    "model_provider": model_config["provider"],
                    "model_name": model_config["model_name"],
                })
                
                # Add edge from parent to this instance
                parent_id = parent_instance_id if parent_instance_id else "baseline"
                graph_data["edges"].append({
                    "from": parent_id,
                    "to": instance_id,
                    "generation": generation,
                })
                
                workflow_data["graph_data"] = graph_data

                # Spawn worker in background
                asyncio.create_task(
                    self._run_worker_instance(instance, workflow_data, baseline_score)
                )

        return instances

    async def _run_worker_instance(
        self,
        instance: dict[str, Any],
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> None:
        """Run a single worker instance.

        Args:
            instance: Instance dictionary
            workflow_data: Workflow data
            baseline_score: Baseline score
        """
        try:
            # Update instance status
            await self._update_instance_status(instance["instance_id"], instance)

            # Get workspace path - run_single_agent_isolated will create its own isolated copy
            repo_dir = workflow_data["repo_dir"]
            main_workspace = self.workspace_root / repo_dir

            # Run worker instance (run in thread pool since it's blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._run_worker_instance_sync,
                instance,
                str(main_workspace),
                workflow_data,
                baseline_score,
            )

            # Store result
            instance["worker_result"] = result
            instance["completed_at"] = time.time()
            instance["status"] = 1  # Still in_progress until evaluated

            # Clean up workspace copy if needed (or keep for evaluation)
            # For now, we'll keep it for evaluation

            await self._update_instance_status(instance["instance_id"], instance)

        except Exception as e:
            instance["error"] = str(e)
            instance["status"] = 2  # rejected
            instance["completed_at"] = time.time()
            await self._update_instance_status(instance["instance_id"], instance)

    def _run_worker_instance_sync(
        self,
        instance: dict[str, Any],
        source_workspace: str,
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> dict[str, Any]:
        """Run worker instance (synchronous version for thread pool).

        Uses the existing run_single_agent_isolated function from worker.cli.
        This function handles workspace isolation internally.

        Args:
            instance: Instance dictionary
            source_workspace: Source workspace path (will be copied to isolated workspace)
            workflow_data: Workflow data
            baseline_score: Baseline score

        Returns:
            Worker result dictionary
        """
        if run_single_agent_isolated is not None:
            # Set API key in environment for the worker
            provider_key_map = {
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GOOGLE_API_KEY",
                "openai": "OPENAI_API_KEY",
            }
            api_key_env = provider_key_map.get(instance["model_provider"])
            
            # Temporarily set API key in environment
            original_key = None
            if api_key_env:
                original_key = os.environ.get(api_key_env)
                os.environ[api_key_env] = instance["api_key"]
            
            try:
                # Use existing worker function (non-Docker, handles workspace isolation)
                # Pass min_improvement_pct to match cli.py behavior
                agent_result, workspace_manager = run_single_agent_isolated(
                    source_workspace=source_workspace,
                    evaluator_path=workflow_data["evaluator_path"],
                    agent_type="optimizer",  # Default agent type
                    agent_id=instance["instance_id"],
                    baseline_score=baseline_score,
                    task=workflow_data["user_prompt"],
                    max_iterations=workflow_data["max_iterations_per_agent"],
                    model_provider=instance["model_provider"],
                    model_name=instance["model_name"],
                    verbosity=1,  # Normal mode for logging (matches cli.py -v)
                    baseline_data=workflow_data.get("baseline_data"),
                    min_improvement_pct=workflow_data.get("min_improvement_pct", 6.0),
                )
                
                # Convert AgentResult to dict format
                result = {
                    "agent_id": agent_result.agent_id,
                    "success": agent_result.success,
                    "score": agent_result.final_score if agent_result.success else baseline_score,
                    "baseline_score": agent_result.baseline_score,
                    "improvement": agent_result.improvement if agent_result.success else 0.0,
                    "error": agent_result.error,
                    "final_score": agent_result.final_score if agent_result.success else None,
                    "duration_seconds": agent_result.duration_seconds,
                    "files_modified": agent_result.files_modified if hasattr(agent_result, 'files_modified') else [],
                }
                
                # Store workspace manager reference if we need to copy changes back later
                # The workspace_manager will be cleaned up automatically, but we can access
                # the workspace path if needed for copying results
                if workspace_manager and agent_result.success:
                    result["workspace_path"] = str(workspace_manager.workspace_path)
                
                return result
            finally:
                # Restore original API key if it existed
                if api_key_env:
                    if original_key is not None:
                        os.environ[api_key_env] = original_key
                    elif api_key_env in os.environ:
                        del os.environ[api_key_env]
        else:
            # Fallback - return error
            return {
                "agent_id": instance["instance_id"],
                "success": False,
                "score": baseline_score,
                "error": "Worker functions not available",
            }

    async def _wait_for_workers(
        self,
        workflow_id: str,
        instances: list[dict[str, Any]],
        time_limit: int,
        early_stop: bool = True,
        min_improvement_pct: float = 6.0,
        current_best_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Wait for workers to complete or time limit.
        
        Supports early stopping when an improvement is found (mirrors cli.py behavior).

        Args:
            workflow_id: Workflow identifier
            instances: List of instances
            time_limit: Time limit in seconds
            early_stop: If True, stop waiting when significant improvement found
            min_improvement_pct: Minimum improvement percentage for early stop
            current_best_score: Current best score for improvement comparison

        Returns:
            List of completed instances
        """
        start_time = time.time()
        improvement_found = False

        while time.time() - start_time < time_limit:
            # Check instance statuses
            completed = [
                inst for inst in instances
                if inst.get("completed_at") is not None or inst.get("status") == 2
            ]

            if len(completed) == len(instances):
                break
            
            # Check for early stop - if any completed instance has significant improvement
            if early_stop and not improvement_found:
                for inst in completed:
                    worker_result = inst.get("worker_result", {})
                    if worker_result.get("success") and worker_result.get("final_score"):
                        final_score = worker_result["final_score"]
                        is_significant, improvement_pct = is_significant_improvement(
                            current_best_score, final_score, min_improvement_pct
                        )
                        if is_significant:
                            logger.info(f"[OptimizationService] ⚡ Early stop triggered - agent {inst.get('instance_id')} found {improvement_pct:.1f}% improvement")
                            improvement_found = True
                            # Give a short grace period for other agents to complete
                            await asyncio.sleep(2)
                            break

            if improvement_found:
                break

            await asyncio.sleep(1)

        # Return all instances that are completed or timed out
        completed_instances = [
            inst for inst in instances
            if inst.get("completed_at") is not None or inst.get("status") == 2
        ]
        
        if improvement_found:
            logger.info(f"[OptimizationService] Early stop: {len(completed_instances)}/{len(instances)} agents completed")
        
        return completed_instances

    async def _evaluate_instances(
        self,
        workflow_id: str,
        instances: list[dict[str, Any]],
        workflow_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate completed worker instances.

        Args:
            workflow_id: Workflow identifier
            instances: List of instances to evaluate
            workflow_data: Workflow data

        Returns:
            List of instances with evaluation scores
        """
        evaluated = []
        baseline_score = workflow_data["baseline_score"]
        generation = workflow_data.get("generation", 0)

        logger.info(f"[OptimizationService] ===== EVALUATING INSTANCES (Generation {generation}) =====")
        logger.info(f"[OptimizationService] Baseline Score: {baseline_score}")
        logger.info(f"[OptimizationService] Evaluating {len(instances)} instances")

        for instance in instances:
            instance_id = instance.get("instance_id", "unknown")
            if instance.get("error"):
                instance["evaluation_score"] = baseline_score
                logger.warning(f"[OptimizationService] Instance {instance_id} has error, using baseline score: {baseline_score}")
                evaluated.append(instance)
                continue

            # Get workspace path for this instance
            instance_workspace = self.workspace_root / f"{workflow_data['repo_dir']}_{instance['instance_id']}"
            evaluator_path = workflow_data["evaluator_path"]

            # Check if workspace exists
            if not instance_workspace.exists():
                instance["error"] = "Instance workspace not found"
                instance["evaluation_score"] = baseline_score
                logger.warning(f"[OptimizationService] Instance {instance_id} workspace not found, using baseline score: {baseline_score}")
                evaluated.append(instance)
                continue

            logger.debug(f"[OptimizationService] Evaluating instance {instance_id}")
            score, error, data = self._run_evaluator(evaluator_path, str(instance_workspace))

            if error:
                instance["error"] = error
                instance["evaluation_score"] = baseline_score
                logger.warning(f"[OptimizationService] Instance {instance_id} evaluation error: {error}, using baseline score: {baseline_score}")
            else:
                instance["evaluation_score"] = score or baseline_score
                instance["evaluation_data"] = data
                
                # Log evaluation values
                improvement = instance["evaluation_score"] - baseline_score
                improvement_pct = (improvement / baseline_score * 100) if baseline_score > 0 else 0
                logger.info(f"[OptimizationService] Instance {instance_id} - Score: {instance['evaluation_score']:.4f} (baseline: {baseline_score:.4f}, improvement: {improvement:+.4f} ({improvement_pct:+.2f}%))")
                if data:
                    logger.info(f"[OptimizationService] Instance {instance_id} - Evaluation Data: {json.dumps(data, indent=2)}")

            evaluated.append(instance)
            await self._update_instance_status(instance["instance_id"], instance)

        logger.info(f"[OptimizationService] ===== EVALUATION COMPLETE =====")
        return evaluated

    def _select_best_instance(
        self, instances: list[dict[str, Any]], baseline_score: float, min_improvement_pct: float = 6.0
    ) -> dict[str, Any] | None:
        """Select the best instance based on evaluation score.
        
        Only considers instances that have significantly improved over the baseline/current best score.
        Uses is_significant_improvement() to filter out noise (same as cli.py).
        Returns None if no instances have improved significantly.

        Args:
            instances: List of evaluated instances
            baseline_score: Current baseline or best score to beat
            min_improvement_pct: Minimum improvement percentage required (default 6%)

        Returns:
            Best instance dictionary that significantly improved over baseline, or None if no significant improvement
        """
        if not instances:
            return None

        # Filter instances with valid scores that significantly improve over baseline
        # This mirrors cli.py's is_significant_improvement check
        significantly_improved_instances = []
        for inst in instances:
            if (inst.get("evaluation_score") is not None 
                and not inst.get("error")):
                score = inst.get("evaluation_score")
                is_significant, improvement_pct = is_significant_improvement(
                    baseline_score, score, min_improvement_pct
                )
                if is_significant:
                    inst["_improvement_pct"] = improvement_pct  # Store for logging
                    significantly_improved_instances.append(inst)
                elif score > baseline_score:
                    # Log instances that improved but below threshold
                    logger.info(f"[OptimizationService] Instance {inst.get('instance_id')} improved but below threshold: {improvement_pct:.1f}% < {min_improvement_pct}%")

        if not significantly_improved_instances:
            return None

        # Sort by score (descending) and return first (best improvement)
        significantly_improved_instances.sort(
            key=lambda x: x["evaluation_score"], reverse=True
        )

        return significantly_improved_instances[0]

    async def _commit_and_push_best_instance(
        self,
        workflow_id: str,
        best_instance: dict[str, Any],
        workflow_data: dict[str, Any],
    ) -> None:
        """Commit and push changes from the best instance.

        Args:
            workflow_id: Workflow identifier
            best_instance: Best instance dictionary
            workflow_data: Workflow data
        """
        repo_dir = workflow_data["repo_dir"]
        branch = workflow_data["branch"]

        # Commit changes
        commit_result = self.github_service.commit_changes(
            repo_dir=repo_dir,
            commit_message=f"Optimization improvement - Generation {workflow_data['generation']} - Score: {best_instance['evaluation_score']:.2f} (baseline: {workflow_data['baseline_score']:.2f})",
            branch=branch,
        )

        if commit_result.get("success"):
            # Push changes
            push_result = self.github_service.push_changes(
                repo_dir=repo_dir,
                branch=branch,
            )
            
            if not push_result.get("success"):
                workflow_data["message"] = f"Committed but failed to push: {push_result.get('error')}"

    async def _update_code_context(
        self,
        workflow_id: str,
        best_instance: dict[str, Any],
        workflow_data: dict[str, Any],
    ) -> None:
        """Update code context with best instance's changes.

        Args:
            workflow_id: Workflow identifier
            best_instance: Best instance dictionary
            workflow_data: Workflow data
        """
        # Copy best instance workspace to main workspace
        repo_dir = workflow_data["repo_dir"]
        main_workspace = self.workspace_root / repo_dir
        best_workspace = self.workspace_root / f"{repo_dir}_{best_instance['instance_id']}"

        if best_workspace.exists():
            # Use existing copy_workspace function if available
            if copy_workspace is not None:
                try:
                    copy_workspace(str(best_workspace), str(main_workspace))
                except Exception as e:
                    workflow_data["message"] = f"Failed to update code context: {e}"
            else:
                # Fallback
                import shutil
                if main_workspace.exists():
                    shutil.rmtree(main_workspace)
                shutil.copytree(best_workspace, main_workspace)

    async def _update_instance_status(
        self, instance_id: str, instance_data: dict[str, Any]
    ) -> None:
        """Update instance status in Redis.

        Args:
            instance_id: Instance identifier
            instance_data: Instance data
        """
        await self.connect()

        instance_key = f"worker_instance:{instance_id}"
        await self.redis_client.setex(
            instance_key, 3600, json.dumps(instance_data)
        )

    async def _save_workflow_state(
        self, workflow_id: str, workflow_data: dict[str, Any]
    ) -> None:
        """Save workflow state to Redis.

        Args:
            workflow_id: Workflow identifier
            workflow_data: Workflow data
        """
        await self.connect()

        workflow_key = f"optimization_workflow:{workflow_id}"
        await self.redis_client.setex(
            workflow_key, 7200, json.dumps(workflow_data)
        )

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """Get workflow status.

        Args:
            workflow_id: Workflow identifier

        Returns:
            OptimizationWorkflowStatus compatible dictionary or None if not found
        """
        await self.connect()

        workflow_key = f"optimization_workflow:{workflow_id}"
        workflow_data = await self.redis_client.get(workflow_key)

        if not workflow_data:
            return None

        data = json.loads(workflow_data)

        # Get latest instance statuses
        instances = []
        for instance in data.get("worker_instances", []):
            instance_id = instance.get("instance_id")
            if instance_id:
                instance_key = f"worker_instance:{instance_id}"
                instance_data = await self.redis_client.get(instance_key)
                if instance_data:
                    instances.append(json.loads(instance_data))
                else:
                    instances.append(instance)

        # Map to response model format
        worker_instances = [
            {
                "instance_id": i.get("instance_id", ""),
                "model_provider": i.get("model_provider", ""),
                "model_name": i.get("model_name", ""),
                "status": i.get("status", 1),
                "evaluation_score": i.get("evaluation_score"),
                "started_at": i.get("started_at"),
                "completed_at": i.get("completed_at"),
                "error": i.get("error"),
                "generation": i.get("generation"),
                "parent_instance_id": i.get("parent_instance_id"),
                "accepted_at_generation": i.get("accepted_at_generation"),
                "rejected_at_generation": i.get("rejected_at_generation"),
            }
            for i in instances
        ]

        # Build graph data
        graph_data = data.get("graph_data", {"nodes": [], "edges": []})

        return {
            "workflow_id": workflow_id,
            "status": data.get("status", "unknown"),
            "repo_dir": data.get("repo_dir", ""),
            "baseline_score": data.get("baseline_score"),
            "current_best_score": data.get("current_best_score"),
            "generation": data.get("generation", 0),
            "total_generations": data.get("total_generations", 0),
            "last_improvement_generation": data.get("last_improvement_generation"),
            "final_generation": data.get("final_generation"),
            "accepted_layers_count": data.get("accepted_layers_count", 0),
            "accepted_generations": data.get("accepted_generations", []),
            "graph_data": graph_data,
            "parent_instance_id": data.get("parent_instance_id"),
            "worker_instances": worker_instances,
            "total_cost": data.get("total_cost", 0.0),
            "message": data.get("message"),
        }
    
    async def pause_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Pause an active workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Result dictionary with success status
        """
        await self.connect()

        workflow_key = f"optimization_workflow:{workflow_id}"
        workflow_data = await self.redis_client.get(workflow_key)

        if not workflow_data:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_id}",
            }

        data = json.loads(workflow_data)
        
        if data.get("status") != "running":
            return {
                "success": False,
                "error": f"Workflow is not running (current status: {data.get('status')})",
            }

        data["status"] = "paused"
        data["paused_at"] = time.time()
        
        await self.redis_client.setex(
            workflow_key, 7200, json.dumps(data)
        )

        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": "paused",
            "message": "Workflow paused successfully",
        }

    async def resume_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Resume a paused workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Result dictionary with success status
        """
        await self.connect()

        workflow_key = f"optimization_workflow:{workflow_id}"
        workflow_data = await self.redis_client.get(workflow_key)

        if not workflow_data:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_id}",
            }

        data = json.loads(workflow_data)
        
        if data.get("status") != "paused":
            return {
                "success": False,
                "error": f"Workflow is not paused (current status: {data.get('status')})",
            }

        data["status"] = "running"
        data["resumed_at"] = time.time()
        
        await self.redis_client.setex(
            workflow_key, 7200, json.dumps(data)
        )

        # Resume workflow execution
        asyncio.create_task(
            self._execute_workflow(workflow_id, data)
        )

        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": "running",
            "message": "Workflow resumed successfully",
        }

    async def stop_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Stop a workflow completely.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Result dictionary with final status
        """
        await self.connect()

        workflow_key = f"optimization_workflow:{workflow_id}"
        workflow_data = await self.redis_client.get(workflow_key)

        if not workflow_data:
            return {
                "success": False,
                "error": f"Workflow not found: {workflow_id}",
            }

        data = json.loads(workflow_data)
        
        data["status"] = "stopped"
        data["stopped_at"] = time.time()
        data["final_generation"] = data.get("generation", 0)
        
        await self.redis_client.setex(
            workflow_key, 7200, json.dumps(data)
        )

        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": "stopped",
            "final_score": data.get("current_best_score"),
            "total_generations": data.get("generation", 0),
            "total_cost": data.get("total_cost", 0.0),
            "message": "Workflow stopped successfully",
        }
    
    async def get_workflow_worker_instances(self, workflow_id: str) -> dict[str, Any]:
        """Get all worker instances for a workflow (internal function, not exposed as API route).

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary with worker instances
        """
        result = await self.get_workflow_status(workflow_id)
        
        if not result.get("success"):
            return result
        
        workflow_data = result.get("workflow", {})
        instances = workflow_data.get("worker_instances", [])
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "instances": instances,
            "count": len(instances),
        }
