"""Optimization workflow service for orchestrating multi-model code optimization."""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import redis.asyncio as redis

from optifiner_api.config import settings
from optifiner_api.services.github_service import GitHubService

# Add worker source to path to import worker functions
_worker_src_path = Path(__file__).parent.parent.parent.parent.parent / "services" / "worker" / "src"
if str(_worker_src_path) not in sys.path:
    sys.path.insert(0, str(_worker_src_path))

# Import existing worker functions
try:
    from worker.cli import run_evaluator, copy_workspace
    from worker.docker_runner import run_agent_in_docker
except ImportError:
    # Fallback if worker modules aren't available
    run_evaluator = None
    copy_workspace = None
    run_agent_in_docker = None

# Thread pool for running Docker commands
_executor = ThreadPoolExecutor(max_workers=10)


class OptimizationService:
    """Service for orchestrating optimization workflows."""

    def __init__(self):
        """Initialize optimization service."""
        self.redis_client: redis.Redis | None = None
        self.github_service = GitHubService()

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
        self, evaluator_path: str, workspace: str, timeout: int = 120
    ) -> tuple[float | None, str | None, dict | None]:
        """Run the evaluator script and return score, error, and full data.

        Uses the existing run_evaluator function from worker.cli if available.

        Args:
            evaluator_path: Path to the evaluator script
            workspace: Path to the workspace to evaluate
            timeout: Timeout in seconds

        Returns:
            Tuple of (score, error, data). If successful, error is None.
        """
        if run_evaluator is not None:
            # Use existing worker function
            try:
                result = run_evaluator(evaluator_path, workspace, timeout, return_full_data=True)
                return result
            except Exception as e:
                return None, f"Error running evaluator: {e}", None
        else:
            # Fallback implementation
            return None, "Worker functions not available - cannot run evaluator", None

    def _find_evaluator(self, repo_dir: str) -> str | None:
        """Find evaluator script in repository.

        Args:
            repo_dir: Directory name of the repository

        Returns:
            Path to evaluator script or None
        """
        repo_path = Path(settings.WORKER_WORKSPACE_PATH) / repo_dir

        # Common evaluator names
        evaluator_names = ["evaluate.py", "evaluator.py", "evaluate.sh", "evaluator.sh"]

        for name in evaluator_names:
            evaluator_path = repo_path / name
            if evaluator_path.exists():
                return str(evaluator_path)

        # Search for any file with "evaluat" in the name
        for file_path in repo_path.rglob("*evaluat*"):
            if file_path.is_file() and file_path.suffix in [".py", ".sh", ".js"]:
                return str(file_path)

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
    ) -> dict[str, Any]:
        """Start an optimization workflow.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone
            total_cost_limit: Total cost limit
            models: List of model configurations
            user_prompt: User prompt
            evaluator_path: Optional path to evaluator script
            max_iterations_per_agent: Max iterations per agent
            time_limit_seconds: Time limit per generation

        Returns:
            Dictionary with workflow information
        """
        await self.connect()

        workflow_id = str(uuid.uuid4())

        # Clone repository
        clone_result = self.github_service.clone_repository(
            repo_url=repo_url,
            branch=branch,
            target_dir=None,  # Use default repo name
        )

        if not clone_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to clone repository: {clone_result.get('error')}",
            }

        repo_dir = clone_result.get("repo_name")
        if not repo_dir:
            return {
                "success": False,
                "error": "Failed to determine repository directory",
            }

        # Create a new branch for optimization workflow
        # Use workflow_id to create a unique branch name
        optimization_branch_name = f"optifiner-{workflow_id[:8]}"
        
        # Get the cloned branch (use the branch that was actually cloned)
        cloned_branch = clone_result.get("branch")
        
        branch_result = self.github_service.create_branch(
            repo_dir=repo_dir,
            branch_name=optimization_branch_name,
            from_branch=cloned_branch,  # Create from the cloned branch
        )

        if not branch_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to create optimization branch: {branch_result.get('error')}",
            }

        # Use the optimization branch for all commits
        optimization_branch = branch_result.get("branch", optimization_branch_name)

        # Find evaluator if not provided
        if not evaluator_path:
            evaluator_path = self._find_evaluator(repo_dir)
            if not evaluator_path:
                return {
                    "success": False,
                    "error": "Evaluator script not found in repository and not provided",
                }

        # Run baseline evaluation
        repo_path = Path(settings.WORKER_WORKSPACE_PATH) / repo_dir
        baseline_score, baseline_error, baseline_data = self._run_evaluator(
            evaluator_path, str(repo_path)
        )

        if baseline_error:
            return {
                "success": False,
                "error": f"Baseline evaluation failed: {baseline_error}",
            }

        if baseline_score is None:
            return {
                "success": False,
                "error": "Baseline evaluation did not return a score",
            }

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
            "worker_instances": [],
            "started_at": time.time(),
            "total_generations": 0,
            "last_improvement_generation": None,
            "accepted_layers_count": 0,
            "accepted_generations": [],  # List of generation numbers that were accepted
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

        Args:
            workflow_id: Workflow identifier
            workflow_data: Initial workflow data
        """
        try:
            generation = workflow_data.get("generation", 0)
            current_best_score = workflow_data.get("current_best_score", workflow_data["baseline_score"])
            total_cost = workflow_data.get("total_cost", 0.0)
            parent_instance_id = workflow_data.get("parent_instance_id", None)

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
                
                # Save workflow state with current generation before starting
                await self._save_workflow_state(workflow_id, workflow_data)

                # Spawn worker instances with parent tracking
                worker_instances = await self._spawn_worker_instances(
                    workflow_id, generation, workflow_data, current_best_score, parent_instance_id
                )

                workflow_data["worker_instances"] = worker_instances
                
                # Save state after spawning instances
                await self._save_workflow_state(workflow_id, workflow_data)

                # Wait for workers to complete or time limit
                completed_instances = await self._wait_for_workers(
                    workflow_id, worker_instances, workflow_data["time_limit_seconds"]
                )

                # Evaluate all completed instances
                evaluated_instances = await self._evaluate_instances(
                    workflow_id, completed_instances, workflow_data
                )

                # Select best instance (only consider instances that improve over current best)
                best_instance = self._select_best_instance(evaluated_instances, current_best_score)

                if not best_instance:
                    # No improvement, stop
                    workflow_data["status"] = "completed"
                    workflow_data["message"] = f"No improvement found at generation {generation}, stopping workflow"
                    workflow_data["final_generation"] = generation
                    break

                # Update best score
                current_best_score = best_instance["evaluation_score"]
                workflow_data["current_best_score"] = current_best_score
                workflow_data["last_improvement_generation"] = generation

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

            # Mark workflow as completed
            workflow_data["status"] = "completed"
            workflow_data["final_generation"] = generation
            workflow_data["total_generations"] = generation
            await self._save_workflow_state(workflow_id, workflow_data)

        except Exception as e:
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

            # Create workspace copy for this instance
            repo_dir = workflow_data["repo_dir"]
            main_workspace = Path(settings.WORKER_WORKSPACE_PATH) / repo_dir
            instance_workspace = Path(settings.WORKER_WORKSPACE_PATH) / f"{repo_dir}_{instance['instance_id']}"

            # Copy workspace using existing function
            if copy_workspace is not None:
                try:
                    copy_workspace(str(main_workspace), str(instance_workspace))
                except Exception as e:
                    raise Exception(f"Failed to copy workspace: {e}")
            else:
                # Fallback
                import shutil
                if instance_workspace.exists():
                    shutil.rmtree(instance_workspace)
                shutil.copytree(main_workspace, instance_workspace)

            # Run worker in Docker (run in thread pool since subprocess is blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._run_worker_in_docker_sync,
                instance,
                str(instance_workspace),
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

    def _run_worker_in_docker_sync(
        self,
        instance: dict[str, Any],
        workspace: str,
        workflow_data: dict[str, Any],
        baseline_score: float,
    ) -> dict[str, Any]:
        """Run worker in Docker container (synchronous version for thread pool).

        Uses the existing run_agent_in_docker function from worker.docker_runner if available.

        Args:
            instance: Instance dictionary
            workspace: Workspace path
            workflow_data: Workflow data
            baseline_score: Baseline score

        Returns:
            Worker result dictionary
        """
        if run_agent_in_docker is not None:
            # Set API key in environment for the Docker runner
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
                # Use existing worker function
                result = run_agent_in_docker(
                    workspace=workspace,
                    evaluator_path=workflow_data["evaluator_path"],
                    agent_type="optimizer",  # Default agent type
                    agent_id=instance["instance_id"],
                    baseline_score=baseline_score,
                    task=workflow_data["user_prompt"],
                    max_iterations=workflow_data["max_iterations_per_agent"],
                    model_provider=instance["model_provider"],
                    model_name=instance["model_name"],
                    timeout=workflow_data["time_limit_seconds"],
                    console=None,  # No console output in async context
                    baseline_data=workflow_data.get("baseline_data"),
                )
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
                "error": "Worker Docker runner not available",
            }

    async def _wait_for_workers(
        self,
        workflow_id: str,
        instances: list[dict[str, Any]],
        time_limit: int,
    ) -> list[dict[str, Any]]:
        """Wait for workers to complete or time limit.

        Args:
            workflow_id: Workflow identifier
            instances: List of instances
            time_limit: Time limit in seconds

        Returns:
            List of completed instances
        """
        start_time = time.time()

        while time.time() - start_time < time_limit:
            # Check instance statuses
            completed = [
                inst for inst in instances
                if inst.get("completed_at") is not None or inst.get("status") == 2
            ]

            if len(completed) == len(instances):
                break

            await asyncio.sleep(1)

        # Return all instances that are completed or timed out
        return [
            inst for inst in instances
            if inst.get("completed_at") is not None or inst.get("status") == 2
        ]

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

        for instance in instances:
            if instance.get("error"):
                instance["evaluation_score"] = workflow_data["baseline_score"]
                evaluated.append(instance)
                continue

            # Get workspace path for this instance
            instance_workspace = Path(settings.WORKER_WORKSPACE_PATH) / f"{workflow_data['repo_dir']}_{instance['instance_id']}"
            evaluator_path = workflow_data["evaluator_path"]

            # Check if workspace exists
            if not instance_workspace.exists():
                instance["error"] = "Instance workspace not found"
                instance["evaluation_score"] = workflow_data["baseline_score"]
                evaluated.append(instance)
                continue

            score, error, data = self._run_evaluator(evaluator_path, str(instance_workspace))

            if error:
                instance["error"] = error
                instance["evaluation_score"] = workflow_data["baseline_score"]
            else:
                instance["evaluation_score"] = score or workflow_data["baseline_score"]
                instance["evaluation_data"] = data

            evaluated.append(instance)
            await self._update_instance_status(instance["instance_id"], instance)

        return evaluated

    def _select_best_instance(
        self, instances: list[dict[str, Any]], baseline_score: float
    ) -> dict[str, Any] | None:
        """Select the best instance based on evaluation score.
        
        Only considers instances that have improved over the baseline/current best score.
        Returns None if no instances have improved.

        Args:
            instances: List of evaluated instances
            baseline_score: Current baseline or best score to beat

        Returns:
            Best instance dictionary that improved over baseline, or None if no improvement
        """
        if not instances:
            return None

        # Filter instances with valid scores that are better than baseline
        improved_instances = [
            inst for inst in instances
            if (inst.get("evaluation_score") is not None 
                and not inst.get("error")
                and inst.get("evaluation_score") > baseline_score)
        ]

        if not improved_instances:
            return None

        # Sort by score (descending) and return first (best improvement)
        improved_instances.sort(
            key=lambda x: x["evaluation_score"], reverse=True
        )

        return improved_instances[0]

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
        main_workspace = Path(settings.WORKER_WORKSPACE_PATH) / repo_dir
        best_workspace = Path(settings.WORKER_WORKSPACE_PATH) / f"{repo_dir}_{best_instance['instance_id']}"

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
