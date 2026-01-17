"""Worker service for task coordination."""

import json
import uuid
from typing import Any

import redis.asyncio as redis
from optifiner_api.config import settings
from optifiner_api.models import EvolutionTask, EvolutionResult


def string_to_agent_type(agent_type_str: str) -> str:
    """Convert string to valid agent type.

    Args:
        agent_type_str: Agent type as string

    Returns:
        Valid agent type string
    """
    valid_types = ["analyzer", "refactoring", "feature", "optimizer"]
    agent_type_lower = agent_type_str.lower()
    if agent_type_lower in valid_types:
        return agent_type_lower
    return "analyzer"  # Default


class WorkerService:
    """Service for coordinating with worker agents."""

    def __init__(self):
        """Initialize worker service."""
        self.redis_client: redis.Redis | None = None

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

    async def submit_task(
        self,
        repo_dir: str,
        agent_type: str,
        task_prompt: str,
        model: str | None = None,
        max_iterations: int = 20,
        metrics: str | None = None,
        baseline: str | None = None,
        analysis: str | None = None,
    ) -> dict[str, Any]:
        """Submit a task to the worker.

        Args:
            repo_dir: Directory name of the repository to work on
            agent_type: Type of agent to use
            task_prompt: Task description/prompt
            model: LLM model to use
            max_iterations: Maximum iterations
            metrics: Metrics description (for analysis/improvement)
            baseline: Baseline description (for analysis/improvement)
            analysis: Analysis result (for improvement)

        Returns:
            Dictionary with task submission information
        """
        await self.connect()

        task_id = str(uuid.uuid4())

        # Normalize agent type
        normalized_agent_type = string_to_agent_type(agent_type)

        # Create task object
        task = EvolutionTask(
            task_id=task_id,
            repo_dir=repo_dir,
            agent_type=normalized_agent_type,
            task_prompt=task_prompt,
            model=model,
            max_iterations=max_iterations,
            metrics=metrics,
            baseline=baseline,
            analysis=analysis,
        )

        # Serialize and store in Redis
        task_key = f"task:{task_id}"
        task_data = {
            "task_id": task.task_id,
            "repo_dir": task.repo_dir,
            "agent_type": task.agent_type,
            "task_prompt": task.task_prompt,
            "model": task.model,
            "max_iterations": task.max_iterations,
            "metrics": task.metrics,
            "baseline": task.baseline,
            "analysis": task.analysis,
            "status": "pending",
        }

        await self.redis_client.setex(
            task_key, 3600, json.dumps(task_data)
        )  # 1 hour TTL

        # Add to task queue
        await self.redis_client.lpush("task_queue", task_id)

        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
        }

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get task status.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with task status
        """
        await self.connect()

        task_key = f"task:{task_id}"
        task_data = await self.redis_client.get(task_key)

        if not task_data:
            return {
                "success": False,
                "error": f"Task not found: {task_id}",
            }

        task_info = json.loads(task_data)

        # Check for result
        result_key = f"result:{task_id}"
        result_data = await self.redis_client.get(result_key)

        if result_data:
            result = json.loads(result_data)
            task_info["result"] = result

        return {
            "success": True,
            "task": task_info,
        }

    async def store_result(self, task_id: str, result: EvolutionResult) -> None:
        """Store worker result.

        Args:
            task_id: Task identifier
            result: Evolution result
        """
        await self.connect()

        # Update task status
        task_key = f"task:{task_id}"
        task_data = await self.redis_client.get(task_key)
        if task_data:
            task_info = json.loads(task_data)
            task_info["status"] = "completed" if result.success else "failed"
            await self.redis_client.setex(task_key, 3600, json.dumps(task_info))

        # Store result
        result_key = f"result:{task_id}"
        result_data = {
            "task_id": result.task_id,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "iterations": result.iterations,
            "messages_count": result.messages_count,
        }
        await self.redis_client.setex(result_key, 3600, json.dumps(result_data))

    async def list_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent tasks.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of task information dictionaries
        """
        await self.connect()

        # Get all task keys
        task_keys = await self.redis_client.keys("task:*")
        tasks = []

        for key in task_keys[:limit]:
            task_data = await self.redis_client.get(key)
            if task_data:
                tasks.append(json.loads(task_data))

        # Sort by task_id (which includes timestamp from UUID)
        tasks.sort(key=lambda x: x.get("task_id", ""), reverse=True)

        return tasks
