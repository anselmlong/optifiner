"""Main worker module for processing evolution tasks."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from optifiner_worker.agents import AgentType
from optifiner_worker.agents.base import run_agent
from optifiner_worker.agents.evolution import (
    run_analysis_agent,
    run_benchmark_generation_agent,
    run_improvement_agent,
)


@dataclass
class EvolutionTask:
    """Task specification for an evolution run."""

    task_id: str
    agent_type: AgentType
    task_prompt: str
    model: str | None = None
    max_iterations: int = 20
    metrics: str | None = None
    baseline: str | None = None
    analysis: str | None = None


@dataclass
class EvolutionResult:
    """Result from an evolution task."""

    task_id: str
    success: bool
    result: str | None
    error: str | None = None
    iterations: int = 0
    messages_count: int = 0


async def process_evolution_task(task: EvolutionTask) -> EvolutionResult:
    """Process a single evolution task.

    Args:
        task: The evolution task to process

    Returns:
        Result of the evolution task
    """
    try:
        if task.agent_type == AgentType.ANALYZER and task.metrics and task.baseline:
            # Run analysis workflow
            state = await run_analysis_agent(
                metrics=task.metrics,
                baseline=task.baseline,
                model=task.model,
            )
        elif task.agent_type != AgentType.ANALYZER and task.metrics and task.baseline and task.analysis:
            # Run improvement workflow
            state = await run_improvement_agent(
                agent_type=task.agent_type,
                metrics=task.metrics,
                baseline=task.baseline,
                analysis=task.analysis,
                model=task.model,
            )
        else:
            # Run generic agent task
            state = await run_agent(
                agent_type=task.agent_type,
                task=task.task_prompt,
                model=task.model,
                max_iterations=task.max_iterations,
            )

        return EvolutionResult(
            task_id=task.task_id,
            success=True,
            result=state.get("result"),
            iterations=state.get("iteration", 0),
            messages_count=len(state.get("messages", [])),
        )

    except Exception as e:
        return EvolutionResult(
            task_id=task.task_id,
            success=False,
            result=None,
            error=str(e),
        )


async def process_benchmark_generation(
    task_id: str,
    benchmark_targets: str,
    model: str | None = None,
) -> EvolutionResult:
    """Generate benchmarks for the codebase.

    Args:
        task_id: Unique task identifier
        benchmark_targets: Description of what to benchmark
        model: LLM model to use

    Returns:
        Result with generated benchmark info
    """
    try:
        state = await run_benchmark_generation_agent(
            benchmark_targets=benchmark_targets,
            model=model,
        )

        return EvolutionResult(
            task_id=task_id,
            success=True,
            result=state.get("result"),
            iterations=state.get("iteration", 0),
            messages_count=len(state.get("messages", [])),
        )

    except Exception as e:
        return EvolutionResult(
            task_id=task_id,
            success=False,
            result=None,
            error=str(e),
        )


# Entry point for testing
if __name__ == "__main__":
    import sys

    async def main():
        # Simple test
        task = EvolutionTask(
            task_id="test-1",
            agent_type=AgentType.ANALYZER,
            task_prompt="List all files in the /app directory and provide a brief summary of the codebase structure.",
            max_iterations=5,
        )

        print(f"Running task: {task.task_id}")
        result = await process_evolution_task(task)
        print(f"Success: {result.success}")
        print(f"Iterations: {result.iterations}")
        print(f"Result: {result.result}")

        if result.error:
            print(f"Error: {result.error}")

    asyncio.run(main())
