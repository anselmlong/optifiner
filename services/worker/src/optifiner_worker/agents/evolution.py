"""Evolution-specific agent workflows."""

from typing import Any

from langchain_core.messages import HumanMessage

from optifiner_worker.agents.base import AgentState, create_agent, run_agent
from optifiner_worker.agents.types import AgentType


ANALYSIS_TASK_TEMPLATE = """Analyze the codebase at /app and identify optimization opportunities.

Target metrics to improve:
{metrics}

Current baseline:
{baseline}

Your task:
1. Explore the codebase structure using ls_tool and glob_tool
2. Read key files to understand the code
3. Identify specific improvement opportunities
4. Rank them by expected impact on the target metrics

Provide your analysis as a structured report with specific file locations and recommended changes."""


IMPROVEMENT_TASK_TEMPLATE = """Improve the codebase at /app to achieve better metrics.

Target metrics to improve:
{metrics}

Current baseline:
{baseline}

Analysis findings:
{analysis}

Your task:
1. Review the analysis findings
2. Implement the most impactful improvement(s)
3. Make targeted, surgical changes using edit_tool or multi_edit_tool
4. Verify changes don't break existing functionality

Focus on changes that will measurably improve the target metrics.
After making changes, summarize what you modified and the expected impact."""


async def run_analysis_agent(
    metrics: str,
    baseline: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Run an analyzer agent to identify improvement opportunities.

    Args:
        metrics: Description of metrics to optimize
        baseline: Current baseline measurements
        model: LLM model to use

    Returns:
        Analysis results
    """
    task = ANALYSIS_TASK_TEMPLATE.format(
        metrics=metrics,
        baseline=baseline,
    )

    return await run_agent(
        agent_type=AgentType.ANALYZER,
        task=task,
        model=model,
        max_iterations=15,
    )


async def run_improvement_agent(
    agent_type: AgentType,
    metrics: str,
    baseline: str,
    analysis: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Run an improvement agent to modify the code.

    Args:
        agent_type: Type of improvement agent (REFACTORING, FEATURE, or OPTIMIZER)
        metrics: Description of metrics to optimize
        baseline: Current baseline measurements
        analysis: Analysis findings to guide improvements
        model: LLM model to use

    Returns:
        Improvement results
    """
    if agent_type == AgentType.ANALYZER:
        raise ValueError("Use run_analysis_agent for analyzer agents")

    task = IMPROVEMENT_TASK_TEMPLATE.format(
        metrics=metrics,
        baseline=baseline,
        analysis=analysis,
    )

    return await run_agent(
        agent_type=agent_type,
        task=task,
        model=model,
        max_iterations=25,
    )


BENCHMARK_GENERATION_TASK = """Analyze the codebase at /app and generate appropriate benchmarks.

The code should be benchmarked for:
{benchmark_targets}

Your task:
1. Explore the codebase to understand its structure and entry points
2. Identify testable functions and components
3. Create benchmark code that measures the specified metrics
4. Write the benchmarks to /app/benchmarks/ directory

The benchmarks should:
- Be deterministic (use fixed random seeds where needed)
- Measure the specified target metrics
- Output results in a parseable format (JSON preferred)
- Include a main entry point for running all benchmarks

Create the benchmark files and provide a summary of what was created."""


async def run_benchmark_generation_agent(
    benchmark_targets: str,
    model: str | None = None,
) -> dict[str, Any]:
    """Run an agent to generate benchmarks for the codebase.

    Args:
        benchmark_targets: Description of what to benchmark
        model: LLM model to use

    Returns:
        Benchmark generation results
    """
    task = BENCHMARK_GENERATION_TASK.format(benchmark_targets=benchmark_targets)

    return await run_agent(
        agent_type=AgentType.ANALYZER,
        task=task,
        model=model,
        max_iterations=20,
    )
