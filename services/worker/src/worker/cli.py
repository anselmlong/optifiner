#!/usr/bin/env python3
"""CLI for testing the evolution agents.

This CLI runs multiple agents on a target repository, each trying to improve
the codebase. Improvements are measured by an evaluator script that returns
a score.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text

# Set up console for rich output
console = Console()


@dataclass
class AgentResult:
    """Result from a single agent run."""
    agent_id: str
    agent_type: str
    success: bool
    baseline_score: float
    final_score: float
    improvement: float = 0.0
    error: str | None = None
    duration_seconds: float = 0.0
    files_modified: list[str] = field(default_factory=list)


@dataclass
class EvolutionState:
    """State of the evolution process."""
    generation: int = 0
    best_score: float = 0.0
    baseline_score: float = 0.0
    total_improvements: int = 0
    total_attempts: int = 0
    history: list[dict] = field(default_factory=list)


def _get_python_executable() -> str:
    """Get the Python executable to use for running scripts."""
    # First try sys.executable (the current Python interpreter)
    if sys.executable:
        return sys.executable
    # Fallback to python3, then python
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    # Last resort
    return "python3"


def run_evaluator(evaluator_path: str, workspace: str, timeout: int = 120) -> tuple[float | None, str | None]:
    """Run the evaluator script and return (score, error).

    Args:
        evaluator_path: Path to the evaluator script.
        workspace: Path to the workspace to evaluate.
        timeout: Timeout in seconds.

    Returns:
        Tuple of (score, error). If successful, error is None.
        If failed, score is None and error contains the error message.
    """
    evaluator = Path(evaluator_path)

    if not evaluator.exists():
        return None, f"Evaluator not found: {evaluator}"

    # Determine how to run the evaluator
    if evaluator.suffix == ".py":
        cmd = [_get_python_executable(), str(evaluator)]
    elif evaluator.suffix == ".sh":
        cmd = ["bash", str(evaluator)]
    elif evaluator.suffix in (".js", ".mjs"):
        cmd = ["node", str(evaluator)]
    else:
        cmd = [str(evaluator)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workspace,
            env={**os.environ, "WORKSPACE_ROOT": workspace},
        )

        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
            return None, f"Evaluator failed (exit {result.returncode}): {error_output[:500]}"

        output = result.stdout.strip()

        # Try to parse as JSON
        try:
            data = json.loads(output)
            score = data.get("score")
            if score is not None:
                return float(score), None
        except json.JSONDecodeError:
            pass

        # Try to extract a number
        import re
        numbers = re.findall(r"[-+]?\d*\.?\d+", output)
        if numbers:
            return float(numbers[0]), None

        return None, f"Could not parse score from evaluator output: {output[:200]}"

    except subprocess.TimeoutExpired:
        return None, f"Evaluator timed out after {timeout} seconds"
    except Exception as e:
        return None, f"Error running evaluator: {e}"


def copy_workspace(source: str, dest: str) -> None:
    """Copy workspace to a new directory."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(source, dest, symlinks=True)


def git_commit(workspace: str, message: str) -> str | None:
    """Create a git commit in the workspace. Returns commit hash or None."""
    try:
        # Check if it's a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.email", "evolution@agent.local"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Evolution Agent"], cwd=workspace, capture_output=True)

        # Stage all changes
        subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace,
            capture_output=True,
        )
        if result.returncode == 0:
            return None  # No changes

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=workspace,
            capture_output=True,
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()[:8]

    except Exception:
        return None


def git_reset(workspace: str) -> None:
    """Reset git workspace to last commit."""
    try:
        subprocess.run(
            ["git", "checkout", "--", "."],
            cwd=workspace,
            capture_output=True,
        )
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=workspace,
            capture_output=True,
        )
    except Exception:
        pass


def run_single_agent(
    workspace: str,
    evaluator_path: str,
    agent_type: str,
    agent_id: str,
    baseline_score: float,
    task: str,
    max_iterations: int,
    model_provider: str,
    model_name: str,
) -> AgentResult:
    """Run a single evolution agent.

    Args:
        workspace: Path to the workspace.
        evaluator_path: Path to the evaluator script.
        agent_type: Type of agent to run.
        agent_id: Unique ID for this agent.
        baseline_score: Current baseline score to beat.
        task: Task description.
        max_iterations: Maximum iterations.
        model_provider: LLM provider.
        model_name: Model name.

    Returns:
        AgentResult with the outcome.
    """
    from worker.config import AgentType, ModelConfig, ModelProvider, WorkerConfig
    from worker.agent import run_evolution_agent, extract_score_from_messages
    from worker.tools.evaluate import set_evaluator

    start_time = time.time()

    # Set up environment
    os.environ["WORKSPACE_ROOT"] = workspace

    # Configure evaluator
    set_evaluator(evaluator_path)

    # Build config
    try:
        config = WorkerConfig(
            model=ModelConfig(
                provider=ModelProvider(model_provider),
                model_name=model_name,
                temperature=0.0,
                max_tokens=8192,
            ),
            agent_type=AgentType(agent_type),
            max_iterations=max_iterations,
            workspace_root=workspace,
        )
    except Exception as e:
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=f"Config error: {e}",
            duration_seconds=time.time() - start_time,
        )

    # Run the agent
    try:
        final_task = f"""Your goal is to improve the codebase to increase its benchmark score.

{task}

Current baseline score: {baseline_score}

IMPORTANT WORKFLOW:
1. First, explore the codebase to understand its structure
2. Make improvements that you believe will increase the score
3. Use the `evaluate` tool to test your changes
4. If score improved above {baseline_score}, you've succeeded!
5. If score is lower or there's an error, try a different approach

Remember: Only improvements that INCREASE the score are kept!"""

        state = run_evolution_agent(
            task=final_task,
            config=config,
            agent_id=agent_id,
            generation=0,
            baseline_score=baseline_score,
        )

        # Try to extract the final score from messages
        final_score = extract_score_from_messages(state.messages)

        # If we couldn't extract from messages, run evaluator directly
        if final_score is None:
            final_score, eval_error = run_evaluator(evaluator_path, workspace)
            if eval_error:
                return AgentResult(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    success=False,
                    baseline_score=baseline_score,
                    final_score=baseline_score,
                    error=eval_error,
                    duration_seconds=time.time() - start_time,
                )

        if final_score is None:
            final_score = baseline_score

        improvement = final_score - baseline_score
        success = improvement > 0

        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=success,
            baseline_score=baseline_score,
            final_score=final_score,
            improvement=improvement,
            duration_seconds=time.time() - start_time,
            files_modified=state.files_modified if hasattr(state, 'files_modified') else [],
        )

    except Exception as e:
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=str(e),
            duration_seconds=time.time() - start_time,
        )


@click.command()
@click.argument("repository", type=click.Path(exists=True))
@click.option("--evaluator", "-e", required=True, type=click.Path(exists=True),
              help="Path to evaluator script that returns a score")
@click.option("--agents", "-n", default=10, help="Number of agents to run (default: 10)")
@click.option("--parallel", "-p", default=1, help="Number of agents to run in parallel (default: 1)")
@click.option("--generations", "-g", default=1, help="Number of evolution generations (default: 1)")
@click.option("--max-iterations", "-i", default=15, help="Max iterations per agent (default: 15)")
@click.option("--task", "-t", default="Improve the code to get a higher benchmark score.",
              help="Task description for agents")
@click.option("--model-provider", default="google",
              type=click.Choice(["anthropic", "google", "openai"]),
              help="LLM provider (default: google)")
@click.option("--model-name", default="gemini-3-flash-preview",
              help="Model name (default: gemini-3-flash-preview)")
@click.option("--output", "-o", type=click.Path(), help="Output file for results (JSON)")
def main(
    repository: str,
    evaluator: str,
    agents: int,
    parallel: int,
    generations: int,
    max_iterations: int,
    task: str,
    model_provider: str,
    model_name: str,
    output: str | None,
):
    """Run evolution agents on a repository to improve its benchmark score.

    REPOSITORY: Path to the target repository to evolve.

    The evaluator script should output a JSON object with a "score" field,
    or just a number. Higher scores are better.

    Example evaluator output:
        {"score": 60.5, "metrics": {"fps": 60.5}}
    or just:
        60.5
    """
    repository_path = Path(repository).resolve()
    evaluator_path = Path(evaluator).resolve()

    console.print(Panel.fit(
        f"[bold cyan]Self-Evolving Code Framework[/bold cyan]\n\n"
        f"Repository: [green]{repository_path}[/green]\n"
        f"Evaluator: [green]{evaluator_path}[/green]\n"
        f"Agents: [yellow]{agents}[/yellow] (parallel: {parallel})\n"
        f"Generations: [yellow]{generations}[/yellow]\n"
        f"Model: [blue]{model_provider}/{model_name}[/blue]",
        title="Evolution Setup"
    ))

    # Get initial baseline score
    console.print("\n[bold]Getting baseline score...[/bold]")
    baseline_score, baseline_error = run_evaluator(str(evaluator_path), str(repository_path))

    if baseline_error:
        console.print(f"[red]Error getting baseline: {baseline_error}[/red]")
        sys.exit(1)

    console.print(f"[green]Baseline score: {baseline_score}[/green]\n")

    # Initialize evolution state
    state = EvolutionState(
        baseline_score=baseline_score,
        best_score=baseline_score,
    )

    # Create initial git commit
    commit_hash = git_commit(str(repository_path), f"Initial state - Score: {baseline_score}")
    if commit_hash:
        console.print(f"[dim]Created initial commit: {commit_hash}[/dim]")

    # Agent types to cycle through
    agent_types = ["optimizer", "refactoring", "feature", "analyzer", "general"]

    # Run evolution generations
    for gen in range(generations):
        state.generation = gen + 1
        console.print(f"\n[bold cyan]═══ Generation {state.generation} ═══[/bold cyan]")
        console.print(f"Current best score: [green]{state.best_score}[/green]")

        generation_results: list[AgentResult] = []

        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(f"[cyan]Running {agents} agents...", total=agents)

            if parallel == 1:
                # Sequential execution
                for i in range(agents):
                    agent_type = agent_types[i % len(agent_types)]
                    agent_id = f"gen{state.generation}-{agent_type}-{i+1}"

                    progress.update(task_id, description=f"[cyan]Agent {i+1}/{agents} ({agent_type})...")

                    # Reset workspace to baseline before each agent
                    git_reset(str(repository_path))

                    result = run_single_agent(
                        workspace=str(repository_path),
                        evaluator_path=str(evaluator_path),
                        agent_type=agent_type,
                        agent_id=agent_id,
                        baseline_score=state.best_score,
                        task=task,
                        max_iterations=max_iterations,
                        model_provider=model_provider,
                        model_name=model_name,
                    )

                    generation_results.append(result)
                    state.total_attempts += 1

                    # Check if improved
                    if result.success and result.final_score > state.best_score:
                        state.best_score = result.final_score
                        state.total_improvements += 1

                        # Commit the improvement
                        commit_msg = (
                            f"Gen {state.generation} | Agent {agent_id}: +{result.improvement:.2f} "
                            f"(Score: {result.baseline_score:.2f} → {result.final_score:.2f})"
                        )
                        commit_hash = git_commit(str(repository_path), commit_msg)

                        console.print(f"\n[green]✓ Agent {agent_id} improved! "
                                      f"Score: {result.baseline_score:.2f} → {result.final_score:.2f} "
                                      f"(+{result.improvement:.2f})[/green]")
                        if commit_hash:
                            console.print(f"[dim]  Committed: {commit_hash}[/dim]")
                    else:
                        # Reset failed changes
                        git_reset(str(repository_path))

                        status = "no improvement" if not result.error else f"error: {result.error[:50]}"
                        console.print(f"[dim]✗ Agent {agent_id}: {status}[/dim]")

                    progress.update(task_id, advance=1)

            else:
                # Parallel execution (each agent gets its own workspace copy)
                temp_workspaces = []

                def run_agent_in_copy(i: int) -> AgentResult:
                    agent_type = agent_types[i % len(agent_types)]
                    agent_id = f"gen{state.generation}-{agent_type}-{i+1}"

                    # Create temp workspace
                    temp_ws = Path(repository_path).parent / f".evolution_temp_{agent_id}_{uuid.uuid4().hex[:6]}"
                    copy_workspace(str(repository_path), str(temp_ws))
                    temp_workspaces.append(str(temp_ws))

                    return run_single_agent(
                        workspace=str(temp_ws),
                        evaluator_path=str(evaluator_path),
                        agent_type=agent_type,
                        agent_id=agent_id,
                        baseline_score=state.best_score,
                        task=task,
                        max_iterations=max_iterations,
                        model_provider=model_provider,
                        model_name=model_name,
                    ), str(temp_ws)

                try:
                    with ThreadPoolExecutor(max_workers=parallel) as executor:
                        futures = {executor.submit(run_agent_in_copy, i): i for i in range(agents)}

                        for future in as_completed(futures):
                            result, temp_ws = future.result()
                            generation_results.append(result)
                            state.total_attempts += 1

                            if result.success and result.final_score > state.best_score:
                                # Copy improved workspace back
                                git_reset(str(repository_path))
                                shutil.rmtree(str(repository_path))
                                shutil.copytree(temp_ws, str(repository_path), symlinks=True)

                                state.best_score = result.final_score
                                state.total_improvements += 1

                                commit_msg = (
                                    f"Gen {state.generation} | Agent {result.agent_id}: "
                                    f"+{result.improvement:.2f}"
                                )
                                git_commit(str(repository_path), commit_msg)

                                console.print(f"\n[green]✓ {result.agent_id} improved! "
                                              f"+{result.improvement:.2f}[/green]")

                            progress.update(task_id, advance=1)

                finally:
                    # Clean up temp workspaces
                    for temp_ws in temp_workspaces:
                        try:
                            shutil.rmtree(temp_ws)
                        except Exception:
                            pass

        # Generation summary
        successful = [r for r in generation_results if r.success]
        console.print(f"\n[bold]Generation {state.generation} Summary:[/bold]")
        console.print(f"  Successful improvements: [green]{len(successful)}/{agents}[/green]")
        console.print(f"  Best score: [cyan]{state.best_score}[/cyan]")

        # Record history
        state.history.append({
            "generation": state.generation,
            "best_score": state.best_score,
            "improvements": len(successful),
            "attempts": agents,
            "results": [
                {
                    "agent_id": r.agent_id,
                    "agent_type": r.agent_type,
                    "success": r.success,
                    "improvement": r.improvement,
                    "duration": r.duration_seconds,
                    "error": r.error,
                }
                for r in generation_results
            ],
        })

    # Final summary
    console.print("\n" + "═" * 50)
    console.print(Panel.fit(
        f"[bold]Evolution Complete![/bold]\n\n"
        f"Initial score: [yellow]{state.baseline_score}[/yellow]\n"
        f"Final score: [green]{state.best_score}[/green]\n"
        f"Total improvement: [cyan]+{state.best_score - state.baseline_score:.2f}[/cyan] "
        f"([cyan]+{((state.best_score - state.baseline_score) / state.baseline_score * 100):.1f}%[/cyan])\n\n"
        f"Successful improvements: {state.total_improvements}/{state.total_attempts}",
        title="Results"
    ))

    # Save results
    if output:
        results_data = {
            "repository": str(repository_path),
            "evaluator": str(evaluator_path),
            "baseline_score": state.baseline_score,
            "final_score": state.best_score,
            "improvement": state.best_score - state.baseline_score,
            "improvement_percent": (state.best_score - state.baseline_score) / state.baseline_score * 100,
            "total_improvements": state.total_improvements,
            "total_attempts": state.total_attempts,
            "generations": state.history,
            "timestamp": datetime.now().isoformat(),
        }
        with open(output, "w") as f:
            json.dump(results_data, f, indent=2)
        console.print(f"\n[dim]Results saved to: {output}[/dim]")


if __name__ == "__main__":
    main()
