#!/usr/bin/env python3
"""CLI for testing the evolution agents.

This CLI runs multiple agents on a target repository, each trying to improve
the codebase. Improvements are measured by a benchmark script that returns
a score.

All execution happens on the host machine with workspace isolation
(/tmp/optifiner_workspaces/) to provide safe sandboxing without containers.

The benchmark script is always at: <workspace_root>/optifiner_benchmark.py
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from worker.observability import AgentObserver, set_observer
from worker.workspace import WorkspaceManager, set_workspace, isolated_workspace, BENCHMARK_SCRIPT_NAME
from worker.evaluator import get_evaluator, evaluate as queue_evaluate

# Set up console for rich output
console = Console()

# Global flag for early stopping
_stop_generation = threading.Event()


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
    if sys.executable:
        return sys.executable
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    return "python3"


def run_evaluator(
    evaluator_path: str, 
    workspace: str, 
    timeout: int = 120,
    return_full_data: bool = False,
) -> tuple[float | None, str | None] | tuple[float | None, str | None, dict | None]:
    """Run the evaluator script using the queue-based evaluator.

    Args:
        evaluator_path: Path to the evaluator script.
        workspace: Path to the workspace to evaluate.
        timeout: Timeout in seconds.
        return_full_data: If True, return full evaluation data as third element.

    Returns:
        Tuple of (score, error) or (score, error, data).
    """
    # Use the queue-based evaluator to prevent simultaneous evaluations
    result = queue_evaluate(workspace, evaluator_path, timeout)
    
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        if return_full_data:
            return None, error, None
        return None, error
    
    score = result.get("score")
    if score is None:
        error = "Evaluator returned no score"
        if return_full_data:
            return None, error, None
        return None, error
    
    if return_full_data:
        # Build data dict from result
        data = {
            "score": score,
            "passed": result.get("passed"),
            "tests_passed": result.get("tests_passed"),
            "tests_total": result.get("tests_total"),
            "metrics": result.get("metrics"),
            "message": result.get("message"),
        }
        # Also include fps if in metrics
        if data.get("metrics") and "fps" in data["metrics"]:
            data["fps"] = data["metrics"]["fps"]
        return float(score), None, data
    
    return float(score), None


def copy_workspace(source: str, dest: str) -> None:
    """Copy workspace to a new directory."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(source, dest, symlinks=True)


def git_commit(workspace: str, message: str) -> str | None:
    """Create a git commit in the workspace. Returns commit hash or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.email", "evolution@agent.local"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Evolution Agent"], cwd=workspace, capture_output=True)

        subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)

        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace,
            capture_output=True,
        )
        if result.returncode == 0:
            return None

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=workspace,
            capture_output=True,
        )

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
        subprocess.run(["git", "checkout", "--", "."], cwd=workspace, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=workspace, capture_output=True)
    except Exception:
        pass


def run_single_agent_isolated(
    source_workspace: str,
    evaluator_path: str,
    agent_type: str,
    agent_id: str,
    baseline_score: float,
    task: str,
    max_iterations: int,
    model_provider: str,
    model_name: str,
    verbosity: int = 1,
    log_dir: str | None = None,
    baseline_data: dict | None = None,
    stop_event: threading.Event | None = None,
) -> tuple[AgentResult, WorkspaceManager | None]:
    """Run a single evolution agent in an isolated workspace.

    Args:
        source_workspace: Path to the source workspace to copy.
        evaluator_path: Path to the evaluator script.
        agent_type: Type of agent to run.
        agent_id: Unique ID for this agent.
        baseline_score: Current baseline score to beat.
        task: Task description.
        max_iterations: Maximum iterations.
        model_provider: LLM provider.
        model_name: Model name.
        verbosity: Observability verbosity.
        log_dir: Optional directory to write agent logs.
        baseline_data: Optional dict with baseline evaluation data.
        stop_event: Optional threading.Event to check for early stopping.

    Returns:
        Tuple of (AgentResult, workspace_manager). Workspace is kept if successful
        so changes can be copied back.
    """
    from worker.config import AgentType, ModelConfig, ModelProvider, WorkerConfig
    from worker.agent import run_evolution_agent, extract_score_from_messages
    from worker.tools.evaluate import set_evaluator

    start_time = time.time()

    # Check if we should stop before even starting
    if stop_event and stop_event.is_set():
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error="Stopped: another agent found improvement",
            duration_seconds=time.time() - start_time,
        ), None

    # Create isolated workspace
    workspace = WorkspaceManager(workspace_id=agent_id[:8])
    try:
        workspace.setup(source_workspace)
    except Exception as e:
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=f"Workspace setup failed: {e}",
            duration_seconds=time.time() - start_time,
        ), None

    # Set the workspace context for tools
    set_workspace(workspace)

    # Configure evaluator to run in the actual workspace
    set_evaluator(evaluator_path)

    # Set up observer
    log_file = None
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = str(Path(log_dir) / f"{agent_id}.jsonl")

    observer = AgentObserver(
        verbosity=verbosity,
        console=console,
        log_file=log_file,
    )
    set_observer(observer)

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
            workspace_root=str(workspace.actual_root),
        )
    except Exception as e:
        observer.close()
        workspace.cleanup()
        set_workspace(None)
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=f"Config error: {e}",
            duration_seconds=time.time() - start_time,
        ), None

    # Build baseline info string
    baseline_info = f"Current baseline score: {baseline_score}"
    if baseline_data:
        if "fps" in baseline_data:
            baseline_info += f"\nBaseline FPS: {baseline_data['fps']:.2f}"
        if "tests_passed" in baseline_data and "tests_total" in baseline_data:
            baseline_info += f"\nBaseline tests: {baseline_data['tests_passed']}/{baseline_data['tests_total']} passed"
        if "metrics" in baseline_data:
            metrics_str = ", ".join(f"{k}={v}" for k, v in baseline_data["metrics"].items())
            baseline_info += f"\nBaseline metrics: {metrics_str}"

    # Run the agent
    try:
        final_task = f"""Your goal is to improve the codebase to increase its benchmark score.

{task}

{baseline_info}

IMPORTANT: The baseline score ({baseline_score}) has already been measured. Do NOT run `evaluate` at the start - this wastes time.

WORKFLOW:
1. Explore the codebase to understand its structure
2. Identify specific optimizations that will improve performance
3. Make targeted improvements
4. THEN use `evaluate` to test your changes
5. If score improved above {baseline_score}, you've succeeded!
6. If score is lower or there's an error, try a different approach

Remember: Only improvements that INCREASE the score are kept!"""

        state = run_evolution_agent(
            task=final_task,
            config=config,
            agent_id=agent_id,
            generation=0,
            baseline_score=baseline_score,
            observer=observer,
        )

        # Extract the final score
        final_score = extract_score_from_messages(state.messages)

        # If we couldn't extract from messages, run evaluator directly
        if final_score is None:
            eval_result = run_evaluator(evaluator_path, str(workspace.actual_root))
            final_score, eval_error = eval_result[0], eval_result[1]
            if eval_error:
                observer.close()
                set_workspace(None)
                workspace.cleanup()
                return AgentResult(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    success=False,
                    baseline_score=baseline_score,
                    final_score=baseline_score,
                    error=eval_error,
                    duration_seconds=time.time() - start_time,
                ), None

        if final_score is None:
            final_score = baseline_score

        improvement = final_score - baseline_score
        success = improvement > 0

        if verbosity >= 2:
            observer.print_summary()

        observer.close()
        set_workspace(None)

        # Keep workspace if successful for copying back
        if not success:
            workspace.cleanup()
            workspace = None

        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=success,
            baseline_score=baseline_score,
            final_score=final_score,
            improvement=improvement,
            duration_seconds=time.time() - start_time,
            files_modified=state.files_modified if hasattr(state, 'files_modified') else [],
        ), workspace

    except Exception as e:
        observer.on_error(str(e))
        observer.close()
        set_workspace(None)
        workspace.cleanup()
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=str(e),
            duration_seconds=time.time() - start_time,
        ), None


def run_benchmark_builder_cli(
    repository_path: Path,
    model_provider: str,
    model_name: str,
    max_iterations: int = 30,
    verbosity: int = 1,
) -> tuple[bool, str, Path | None]:
    """Run the benchmark builder agent to create optifiner_benchmark.py.
    
    Args:
        repository_path: Path to the target repository.
        model_provider: LLM provider.
        model_name: Model name.
        max_iterations: Maximum iterations for the agent.
        verbosity: Verbosity level.
        
    Returns:
        Tuple of (success, message, benchmark_path).
    """
    from worker.benchmark_builder import run_benchmark_builder
    from worker.config import ModelConfig, ModelProvider
    
    console.print("\n[bold cyan]Running Benchmark Builder Agent...[/bold cyan]")
    console.print(f"[dim]This agent will:[/dim]")
    console.print(f"[dim]  1. Analyze the codebase[/dim]")
    console.print(f"[dim]  2. Modify files to expose metrics (FPS, timing, etc.) if needed[/dim]")
    console.print(f"[dim]  3. Create {BENCHMARK_SCRIPT_NAME} benchmark script[/dim]")
    console.print(f"[dim]  4. Test and iterate until it works[/dim]")
    console.print(f"[dim]All changes become the baseline for evolution agents.[/dim]")
    
    # Create workspace for benchmark builder
    workspace = WorkspaceManager(workspace_id="benchmark-builder")
    workspace.setup(repository_path)
    
    # Set up observer
    observer = AgentObserver(
        verbosity=verbosity,
        console=console,
    )
    set_observer(observer)
    
    try:
        model_config = ModelConfig(
            provider=ModelProvider(model_provider),
            model_name=model_name,
            temperature=0.0,
            max_tokens=8192,
        )
        
        success, message = run_benchmark_builder(
            workspace=workspace,
            max_iterations=max_iterations,
            model_config=model_config,
            observer=observer,
        )
        
        if success:
            # Copy ALL changes back to the original repo (not just the benchmark script)
            # The benchmark builder may have modified the codebase to expose metrics
            # These modifications become the baseline for evolution agents
            console.print(f"[dim]Copying all modifications back to repository...[/dim]")
            
            modified_files = []
            for item in workspace.actual_root.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(workspace.actual_root)
                    
                    # Skip git internals
                    if ".git" in rel_path.parts:
                        continue
                    
                    dst_path = repository_path / rel_path
                    src_path = item
                    
                    # Check if file is new or modified
                    is_new = not dst_path.exists()
                    is_modified = False
                    if dst_path.exists():
                        try:
                            is_modified = src_path.read_bytes() != dst_path.read_bytes()
                        except Exception:
                            pass
                    
                    if is_new or is_modified:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        modified_files.append(str(rel_path))
            
            if modified_files:
                console.print(f"[green]✓ Modified {len(modified_files)} file(s):[/green]")
                for f in modified_files[:10]:  # Show first 10
                    console.print(f"[dim]  - {f}[/dim]")
                if len(modified_files) > 10:
                    console.print(f"[dim]  ... and {len(modified_files) - 10} more[/dim]")
            
            benchmark_path = repository_path / BENCHMARK_SCRIPT_NAME
            if benchmark_path.exists():
                console.print(f"[green]✓ Benchmark script ready at {benchmark_path}[/green]")
                return True, message, benchmark_path
            else:
                console.print(f"[red]✗ {BENCHMARK_SCRIPT_NAME} not created[/red]")
                return False, "Benchmark script was not created", None
        
        console.print(f"[red]✗ Benchmark builder failed: {message}[/red]")
        return False, message, None
        
    finally:
        workspace.cleanup()
        set_workspace(None)
        observer.close()


@click.command()
@click.argument("repository", type=click.Path(exists=True))
@click.option("--evaluator", "-e", type=click.Path(),
              help="Path to evaluator script. If not provided, will run benchmark builder to create one.")
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
@click.option("--verbose", "-v", count=True, default=1,
              help="Increase verbosity (-v=normal, -vv=verbose, -vvv=debug, omit for quiet)")
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode - minimal output (overrides -v)")
@click.option("--log-dir", "-l", type=click.Path(),
              help="Directory to save agent execution logs (JSONL format)")
@click.option("--early-stop/--no-early-stop", default=True,
              help="Stop generation early when improvement found (default: enabled)")
@click.option("--build-benchmark", "-b", is_flag=True,
              help="Run benchmark builder agent to create optifiner_benchmark.py")
def main(
    repository: str,
    evaluator: str | None,
    agents: int,
    parallel: int,
    generations: int,
    max_iterations: int,
    task: str,
    model_provider: str,
    model_name: str,
    output: str | None,
    verbose: int,
    quiet: bool,
    log_dir: str | None,
    early_stop: bool,
    build_benchmark: bool,
):
    """Run evolution agents on a repository to improve its benchmark score.

    REPOSITORY: Path to the target repository to evolve.

    The benchmark script must output JSON with these required fields:
        - score: Primary metric value (number, non-null)
        - metric_name: Name of the metric (e.g., "FPS", "throughput")
        - test_gate: Boolean, must be true for valid run

    Example output:
        {"score": 60.5, "metric_name": "FPS", "test_gate": true, "metrics": {...}}

    If no benchmark exists, use --build-benchmark to automatically
    create one using the Benchmark Builder Agent.

    VERBOSITY LEVELS:
        (no flags): quiet mode - only show progress and results
        -v: normal - show iteration progress, tool calls (compact)
        -vv: verbose - show agent reasoning, full tool calls/results
        -vvv: debug - show everything including full system prompts
    
    EARLY STOPPING:
        By default, when an agent finds an improvement, the current generation
        stops and a new generation begins with the improved codebase.
        Use --no-early-stop to disable this behavior.
    """
    global _stop_generation
    
    repository_path = Path(repository).resolve()
    
    # Determine verbosity level
    verbosity = 0 if quiet else verbose

    # Resolve log directory
    log_directory = str(Path(log_dir).resolve()) if log_dir else None

    # Handle evaluator
    evaluator_path: Path | None = None
    
    if evaluator:
        evaluator_path = Path(evaluator).resolve()
        if not evaluator_path.exists():
            console.print(f"[red]Error: Evaluator not found: {evaluator_path}[/red]")
            sys.exit(1)
    else:
        # Check for benchmark script - try new name first, then legacy name
        benchmark_path = repository_path / BENCHMARK_SCRIPT_NAME
        legacy_path = repository_path / "run_validator.py"
        
        if benchmark_path.exists():
            evaluator_path = benchmark_path
            console.print(f"[dim]Using existing benchmark: {evaluator_path}[/dim]")
        elif legacy_path.exists():
            evaluator_path = legacy_path
            console.print(f"[dim]Using legacy benchmark: {evaluator_path}[/dim]")
        elif build_benchmark:
            # Explicitly requested to build benchmark
            success, message, created_path = run_benchmark_builder_cli(
                repository_path,
                model_provider,
                model_name,
                max_iterations=30,
                verbosity=verbosity,
            )
            
            if not success:
                console.print(f"[red]Failed to create benchmark: {message}[/red]")
                sys.exit(1)
            
            evaluator_path = created_path
        else:
            # No benchmark found, need to build one
            console.print(f"[yellow]No benchmark found ({BENCHMARK_SCRIPT_NAME} or run_validator.py).[/yellow]")
            console.print("[yellow]Running benchmark builder agent to create one...[/yellow]")
            
            success, message, created_path = run_benchmark_builder_cli(
                repository_path,
                model_provider,
                model_name,
                max_iterations=30,
                verbosity=verbosity,
            )
            
            if not success:
                console.print(f"[red]Failed to create benchmark: {message}[/red]")
                sys.exit(1)
            
            evaluator_path = created_path

    if evaluator_path is None:
        console.print("[red]Error: No evaluator available[/red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold cyan]Self-Evolving Code Framework[/bold cyan]\n\n"
        f"Repository: [green]{repository_path}[/green]\n"
        f"Evaluator: [green]{evaluator_path}[/green]\n"
        f"Agents: [yellow]{agents}[/yellow] (parallel: {parallel})\n"
        f"Generations: [yellow]{generations}[/yellow]\n"
        f"Model: [blue]{model_provider}/{model_name}[/blue]\n"
        f"Verbosity: [magenta]{['quiet', 'normal', 'verbose', 'debug'][min(verbosity, 3)]}[/magenta]\n"
        f"Early stop: [{'green' if early_stop else 'dim'}]{early_stop}[/{'green' if early_stop else 'dim'}]"
        + (f"\nLog dir: [dim]{log_directory}[/dim]" if log_directory else ""),
        title="Evolution Setup"
    ))

    # Get initial baseline score with full data
    console.print("\n[bold]Getting baseline score...[/bold]")
    baseline_result = run_evaluator(str(evaluator_path), str(repository_path), return_full_data=True)
    baseline_score, baseline_error, baseline_data = baseline_result

    if baseline_error:
        console.print(f"[red]Error getting baseline: {baseline_error}[/red]")
        console.print("[yellow]Tip: Make sure your evaluator script works correctly.[/yellow]")
        sys.exit(1)

    console.print(f"[green]Baseline score: {baseline_score}[/green]")
    if baseline_data:
        if "fps" in baseline_data:
            console.print(f"[dim]  FPS: {baseline_data['fps']:.2f}[/dim]")
        if baseline_data.get("tests_passed") is not None and baseline_data.get("tests_total") is not None:
            console.print(f"[dim]  Tests: {baseline_data['tests_passed']}/{baseline_data['tests_total']}[/dim]")
        if baseline_data.get("metrics"):
            for k, v in baseline_data["metrics"].items():
                if k not in ("fps",):
                    console.print(f"[dim]  {k}: {v}[/dim]")
    console.print()

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

    # Track current baseline data for agents
    current_baseline_data = baseline_data

    # Run evolution generations
    gen = 0
    while gen < generations:
        gen += 1
        state.generation = gen
        _stop_generation.clear()
        
        console.print(f"\n[bold cyan]═══ Generation {state.generation} ═══[/bold cyan]")
        console.print(f"Current best score: [green]{state.best_score}[/green]")

        generation_results: list[AgentResult] = []
        generation_improved = False

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
                    if early_stop and _stop_generation.is_set():
                        console.print(f"[yellow]⚡ Early stop triggered - starting new generation[/yellow]")
                        break
                    
                    agent_type = agent_types[i % len(agent_types)]
                    agent_id = f"gen{state.generation}-{agent_type}-{i+1}"

                    progress.update(task_id, description=f"[cyan]Agent {i+1}/{agents} ({agent_type})...")

                    result, workspace = run_single_agent_isolated(
                        source_workspace=str(repository_path),
                        evaluator_path=str(evaluator_path),
                        agent_type=agent_type,
                        agent_id=agent_id,
                        baseline_score=state.best_score,
                        task=task,
                        max_iterations=max_iterations,
                        model_provider=model_provider,
                        model_name=model_name,
                        verbosity=verbosity,
                        log_dir=log_directory,
                        baseline_data=current_baseline_data,
                        stop_event=_stop_generation if early_stop else None,
                    )

                    generation_results.append(result)
                    state.total_attempts += 1

                    # Check if improved
                    if result.success and result.final_score > state.best_score and workspace:
                        # Copy improved workspace back to original
                        git_reset(str(repository_path))
                        
                        # Remove original files and copy improved version
                        for item in repository_path.iterdir():
                            if item.name != ".git":
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                        
                        for item in workspace.actual_root.iterdir():
                            if item.name != ".git":
                                if item.is_dir():
                                    shutil.copytree(item, repository_path / item.name)
                                else:
                                    shutil.copy2(item, repository_path / item.name)

                        state.best_score = result.final_score
                        state.total_improvements += 1
                        generation_improved = True

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

                        # Update baseline data
                        new_result = run_evaluator(str(evaluator_path), str(repository_path), return_full_data=True)
                        if new_result[0] is not None:
                            current_baseline_data = new_result[2]

                        if early_stop:
                            _stop_generation.set()
                    else:
                        status = "no improvement" if not result.error else f"error: {result.error[:50]}"
                        console.print(f"[dim]✗ Agent {agent_id}: {status}[/dim]")

                    # Clean up workspace if we kept it
                    if workspace:
                        workspace.cleanup()

                    progress.update(task_id, advance=1)

            else:
                # Parallel execution
                def run_agent_parallel(i: int) -> tuple[AgentResult, WorkspaceManager | None]:
                    agent_type = agent_types[i % len(agent_types)]
                    agent_id = f"gen{state.generation}-{agent_type}-{i+1}"
                    
                    return run_single_agent_isolated(
                        source_workspace=str(repository_path),
                        evaluator_path=str(evaluator_path),
                        agent_type=agent_type,
                        agent_id=agent_id,
                        baseline_score=state.best_score,
                        task=task,
                        max_iterations=max_iterations,
                        model_provider=model_provider,
                        model_name=model_name,
                        verbosity=0,  # Quiet in parallel
                        log_dir=log_directory,
                        baseline_data=current_baseline_data,
                        stop_event=_stop_generation if early_stop else None,
                    )

                try:
                    with ThreadPoolExecutor(max_workers=parallel) as executor:
                        futures = {executor.submit(run_agent_parallel, i): i for i in range(agents)}

                        for future in as_completed(futures):
                            if early_stop and _stop_generation.is_set() and generation_improved:
                                for f in futures:
                                    f.cancel()
                                console.print(f"[yellow]⚡ Early stop - cancelling remaining agents[/yellow]")
                                break

                            try:
                                result, workspace = future.result()
                            except Exception:
                                progress.update(task_id, advance=1)
                                continue

                            generation_results.append(result)
                            state.total_attempts += 1

                            if result.success and result.final_score > state.best_score and workspace:
                                git_reset(str(repository_path))
                                
                                for item in repository_path.iterdir():
                                    if item.name != ".git":
                                        if item.is_dir():
                                            shutil.rmtree(item)
                                        else:
                                            item.unlink()
                                
                                for item in workspace.actual_root.iterdir():
                                    if item.name != ".git":
                                        if item.is_dir():
                                            shutil.copytree(item, repository_path / item.name)
                                        else:
                                            shutil.copy2(item, repository_path / item.name)

                                state.best_score = result.final_score
                                state.total_improvements += 1
                                generation_improved = True

                                commit_msg = f"Gen {state.generation} | Agent {result.agent_id}: +{result.improvement:.2f}"
                                git_commit(str(repository_path), commit_msg)

                                console.print(f"\n[green]✓ {result.agent_id} improved! +{result.improvement:.2f}[/green]")

                                new_result = run_evaluator(str(evaluator_path), str(repository_path), return_full_data=True)
                                if new_result[0] is not None:
                                    current_baseline_data = new_result[2]

                                if early_stop:
                                    _stop_generation.set()

                            if workspace:
                                workspace.cleanup()

                            progress.update(task_id, advance=1)

                except Exception as e:
                    console.print(f"[red]Error in parallel execution: {e}[/red]")

        # Generation summary
        successful = [r for r in generation_results if r.success]
        console.print(f"\n[bold]Generation {state.generation} Summary:[/bold]")
        console.print(f"  Successful improvements: [green]{len(successful)}/{len(generation_results)}[/green]")
        console.print(f"  Best score: [cyan]{state.best_score}[/cyan]")

        state.history.append({
            "generation": state.generation,
            "best_score": state.best_score,
            "improvements": len(successful),
            "attempts": len(generation_results),
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

        if early_stop and generation_improved and gen < generations:
            console.print(f"[cyan]Starting new generation with improved codebase...[/cyan]")

    # Final summary
    console.print("\n" + "═" * 50)
    improvement_pct = ((state.best_score - state.baseline_score) / state.baseline_score * 100) if state.baseline_score > 0 else 0
    console.print(Panel.fit(
        f"[bold]Evolution Complete![/bold]\n\n"
        f"Initial score: [yellow]{state.baseline_score}[/yellow]\n"
        f"Final score: [green]{state.best_score}[/green]\n"
        f"Total improvement: [cyan]+{state.best_score - state.baseline_score:.2f}[/cyan] "
        f"([cyan]+{improvement_pct:.1f}%[/cyan])\n\n"
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
            "improvement_percent": improvement_pct,
            "total_improvements": state.total_improvements,
            "total_attempts": state.total_attempts,
            "generations": state.history,
            "timestamp": datetime.now().isoformat(),
            "early_stop": early_stop,
        }
        with open(output, "w") as f:
            json.dump(results_data, f, indent=2)
        console.print(f"\n[dim]Results saved to: {output}[/dim]")


if __name__ == "__main__":
    main()
